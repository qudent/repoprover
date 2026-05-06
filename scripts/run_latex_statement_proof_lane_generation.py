#!/usr/bin/env python3
"""Generate proof-lane solution outputs from target-hidden task dossiers."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from openai import OpenAI

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.run_latex_statement_generation import (  # noqa: E402
    DEFAULT_BASE_URL,
    DEFAULT_MODEL,
    completed_generation_batch_summary,
    enforce_generation_contracts,
    extract_message_content,
    maybe_parse_json,
    response_cost_summary,
    scrub_lean_snippet_comments,
    summarize_costs,
    write_json,
)
from scripts.run_latex_statement_generation_repair import load_generation_output  # noqa: E402


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def unique_in_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value and value not in seen:
            out.append(value)
            seen.add(value)
    return out


def task_paths(task_dir: Path) -> list[Path]:
    tasks_dir = task_dir / "tasks"
    if tasks_dir.exists():
        return sorted(tasks_dir.glob("*.json"))
    if task_dir.is_file():
        return [task_dir]
    return []


def load_tasks(task_dir: Path, unit_keys: set[str] | None = None) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    for path in task_paths(task_dir):
        task = read_json(path)
        unit_key = str(task.get("unit_key") or "")
        if unit_keys and unit_key not in unit_keys:
            continue
        tasks.append(task)
    if not tasks:
        requested = f" for requested units {sorted(unit_keys)}" if unit_keys else ""
        raise ValueError(f"no proof-lane tasks found in {task_dir}{requested}")
    return tasks


def load_decline_context_pack(path: Path | None) -> dict[tuple[str, str], dict[str, Any]]:
    if path is None:
        return {}
    data = read_json(path)
    packs: dict[tuple[str, str], dict[str, Any]] = {}
    for unit in data.get("units") or []:
        source_unit_id = str(unit.get("source_unit_id") or "")
        unit_key = str(unit.get("unit_key") or "")
        if source_unit_id and unit_key:
            packs[(source_unit_id, unit_key)] = unit
    return packs


def attach_decline_context_pack(tasks: list[dict[str, Any]], pack_path: Path | None) -> int:
    packs = load_decline_context_pack(pack_path)
    attached = 0
    if not packs:
        return attached
    for task in tasks:
        unit_key = str(task.get("unit_key") or "")
        source_unit_id = str((task.get("source_unit") or {}).get("id") or "")
        pack = packs.get((source_unit_id, unit_key))
        if not pack:
            continue
        context = pack.get("selected_project_context") or []
        if not context:
            continue
        task["decline_context_pack"] = {
            "source": "scripts/build_proof_lane_decline_context_pack.py",
            "policy": (
                "Additional project context acquired from clean proof-lane decline notes after "
                "same-source target-declaration exclusion filtering. Use these snippets as visible "
                "project context; do not infer hidden aligned target declarations."
            ),
            "selected_project_context": context,
        }
        attached += 1
    return attached


def chunks(items: list[dict[str, Any]], size: int) -> list[list[dict[str, Any]]]:
    if size <= 0 or size >= len(items):
        return [items]
    return [items[index : index + size] for index in range(0, len(items), size)]


def build_messages(tasks: list[dict[str, Any]]) -> list[dict[str, str]]:
    system = (
        "You are a Lean 4 proof-synthesis coding agent. Solve target-hidden "
        "LaTeX-statement proof-lane tasks by producing complete Lean declarations "
        "from only the visible source/context dossier. The aligned target Lean "
        "declarations are withheld. Return exactly one JSON object."
    )
    user = {
        "task": (
            "For each proof-lane task, try to produce a complete Lean file body "
            "that formalizes the visible source unit. If visible source/project/"
            "local/Mathlib context is still insufficient, return a clean "
            "cannot_prove_from_visible_context unit and identify the missing "
            "checked facts in notes."
        ),
        "required_json_schema": {
            "units": [
                {
                    "unit_key": "unit-001",
                    "status": "generated|cannot_prove_from_visible_context",
                    "lean_file_body": (
                        "if status is generated: complete Lean declarations only, no imports or markdown; "
                        "if status is cannot_prove_from_visible_context: exactly empty string"
                    ),
                    "declaration_names": [
                        "names introduced in lean_file_body; empty list when status is cannot_prove_from_visible_context"
                    ],
                    "used_context": ["source/project/local/Mathlib facts actually used"],
                    "notes": ["brief proof strategy, caveats, or precise missing checked facts"],
                }
            ]
        },
        "instructions": [
            "Do not use sorry, admit, placeholders, ellipses, or comments standing in for proof.",
            "Do not include imports or markdown fences in lean_file_body.",
            "Do not inspect, infer, ask for, or name hidden aligned Lean target declarations.",
            "Use only the source text, visible prompt context, verifier-visible support context, and checked Mathlib/project/local facts shown in each task.",
            "Treat selector sketches and previous failed generations as diagnostic intent only; Lean-checked signatures and visible source text are authoritative.",
            "You may introduce same-unit helper definitions or lemmas before the main declaration when they are justified by visible source/context.",
            "Do not use a helper name as an existing fact until you have defined/proved it earlier in the same lean_file_body.",
            "Keep theorem statements source-shaped. Do not replace elementary source hypotheses by stronger library predicates unless you also construct those predicates locally in the proof.",
            "If a checked bridge lemma rewrites between indexed forms, use an explicit rw/change/calc route in the direction of the goal.",
            "For finite sums and products over a Finset, use Lean membership-binder notation `sum x in s` is invalid; write Lean syntax as `∑ x ∈ s, f x` or `∏ x ∈ s, f x`.",
            "Do not enlarge a finite source choice space to all functions into an infinite codomain. Preserve finite representations supplied by visible context.",
            "Every identifier in a generated declaration must be introduced by an explicit binder, local declaration, visible helper, checked Mathlib/project/local declaration, or import/open context visible to the verifier.",
            "If verifier messages report missing typeclass instances for an unbound symbol, such as `Zero K`, `CommRing K`, or `Fintype α`, add the required type variable and typeclass binders to the generated theorem or emit the corresponding visible `variable` command in lean_file_body. Do not rely on local_file_context_candidates variables unless you reproduce the needed variable command or binders in the output.",
            "If a task contains decline_context_pack.selected_project_context, treat those snippets as newly acquired visible project/local context after target-hidden filtering. Try those project declarations before concluding that a named project definition or bridge is unavailable.",
            "Do not describe a declaration as missing if its name appears in decline_context_pack.selected_project_context. If you still cannot use that declaration, notes must state the concrete reason: unresolved dependency, namespace/import mismatch, type/signature mismatch, or proof-synthesis gap.",
            "If the visible context is insufficient, set status to cannot_prove_from_visible_context, lean_file_body to exactly empty string, and declaration_names to exactly []. Put the missing facts in notes only.",
        ],
        "benchmark_policy": {
            "target_lean_available_to_proof_lane_generator": False,
            "posthoc_alignment_hidden": True,
            "gold_comparison_is_posthoc_only": True,
        },
        "proof_lane_tasks": scrub_lean_snippet_comments(tasks),
    }
    return [{"role": "system", "content": system}, {"role": "user", "content": json.dumps(user, indent=2, sort_keys=True, ensure_ascii=False)}]


def aggregate_outputs(paths: list[Path]) -> dict[str, Any] | None:
    units: list[dict[str, Any]] = []
    for path in paths:
        output = load_generation_output(path)
        units.extend(output.get("units") or [])
    if not units:
        return None
    return {
        "schema_version": "repoprover.latex_statement_proof_lane_generation_aggregated.v1",
        "unit_keys": unique_in_order([str(unit.get("unit_key") or "") for unit in units]),
        "units": units,
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    run_dir = args.output
    eval_dir = run_dir / "eval"
    eval_dir.mkdir(parents=True, exist_ok=True)

    selected_tasks = load_tasks(args.proof_lane_task_dir, set(args.unit_key or []) or None)
    decline_context_pack = getattr(args, "decline_context_pack", None)
    attached_decline_context_pack_count = attach_decline_context_pack(selected_tasks, decline_context_pack)
    task_chunks = chunks(selected_tasks, args.max_tasks_per_call)
    summary: dict[str, Any] = {
        "schema_version": "repoprover.latex_statement_proof_lane_generation.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "proof_lane_task_dir": str(args.proof_lane_task_dir),
        "output_path": str(run_dir),
        "model": args.model,
        "reasoning_effort": args.reasoning_effort,
        "temperature": args.temperature,
        "max_tokens": args.max_tokens,
        "max_tasks_per_call": args.max_tasks_per_call,
        "budget_only": args.budget_only,
        "resume_existing": bool(getattr(args, "resume_existing", False)),
        "paid_call_made": False,
        "task_unit_keys": [str(task.get("unit_key") or "") for task in selected_tasks],
        "decline_context_pack": str(decline_context_pack) if decline_context_pack else None,
        "attached_decline_context_pack_count": attached_decline_context_pack_count,
        "batch_count": len(task_chunks),
        "batches": [],
    }

    output_paths: list[Path] = []
    client: OpenAI | None = None

    for batch_index, batch_tasks in enumerate(task_chunks, start=1):
        batch_dir = run_dir / f"batch-{batch_index:03d}"
        batch_dir.mkdir(parents=True, exist_ok=True)
        messages = build_messages(batch_tasks)
        request_payload: dict[str, Any] = {
            "model": args.model,
            "messages": messages,
            "temperature": args.temperature,
            "max_tokens": args.max_tokens,
            "response_format": {"type": "json_object"},
        }
        if args.reasoning_effort:
            request_payload["extra_body"] = {"reasoning": {"effort": args.reasoning_effort, "exclude": True}}
        write_json(batch_dir / "generation-payload.json", request_payload)
        batch_summary: dict[str, Any] = {
            "batch_index": batch_index,
            "task_unit_keys": [str(task.get("unit_key") or "") for task in batch_tasks],
            "payload_path": str(batch_dir / "generation-payload.json"),
            "budget_only": args.budget_only,
            "paid_call_made": False,
            "valid_json": False,
            "parse_error": None,
        }
        if args.budget_only:
            summary["batches"].append(batch_summary)
            continue
        if getattr(args, "resume_existing", False):
            completed = completed_generation_batch_summary(batch_dir, args.model)
            if completed is not None:
                batch_summary.update(completed)
                output_paths.append(batch_dir / "generation-output.json")
                summary["batches"].append(batch_summary)
                continue

        if client is None:
            if not os.getenv("OPENROUTER_API_KEY"):
                raise RuntimeError("OPENROUTER_API_KEY is not set")
            client = OpenAI(api_key=os.environ["OPENROUTER_API_KEY"], base_url=args.base_url)
        started = time.monotonic()
        try:
            response = client.chat.completions.create(**request_payload)
        except Exception as exc:  # noqa: BLE001 - provider/client failures must be logged and resumable.
            error_text = "".join(traceback.format_exception(exc))
            (batch_dir / "provider-error.txt").write_text(error_text, encoding="utf-8")
            batch_summary["provider_error"] = {
                "type": type(exc).__name__,
                "message": str(exc),
                "traceback_path": str(batch_dir / "provider-error.txt"),
            }
            summary["batches"].append(batch_summary)
            continue
        batch_summary["elapsed_seconds"] = round(time.monotonic() - started, 3)
        batch_summary["paid_call_made"] = True
        summary["paid_call_made"] = True
        write_json(batch_dir / "generation-response.json", response.model_dump())
        content = extract_message_content(response)
        (batch_dir / "generation-assistant-content.txt").write_text(content, encoding="utf-8")
        parsed, parse_error = maybe_parse_json(content)
        batch_summary["parse_error"] = parse_error
        batch_summary["valid_json"] = parsed is not None
        batch_summary["cost_summary"] = response_cost_summary(response, args.model)
        if parsed is not None:
            normalized, contract_report = enforce_generation_contracts(parsed)
            if contract_report["normalized_unit_count"]:
                write_json(batch_dir / "raw-generation-output.json", parsed)
            batch_summary["contract_enforcement"] = contract_report
            output_path = batch_dir / "generation-output.json"
            write_json(output_path, normalized)
            output_paths.append(output_path)
        summary["batches"].append(batch_summary)

    if output_paths:
        aggregated = aggregate_outputs(output_paths)
        if aggregated is not None:
            write_json(eval_dir / "merged-generation-output.json", aggregated)
    summary["cost_summary"] = summarize_costs(summary["batches"], args.model)
    provider_errors = [row.get("provider_error") for row in summary["batches"] if row.get("provider_error")]
    summary["provider_error_count"] = len(provider_errors)
    if provider_errors:
        summary["provider_errors"] = provider_errors
    write_json(eval_dir / "generation-results.json", summary)
    write_json(eval_dir / "proof-lane-generation-results.json", summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--proof-lane-task-dir", type=Path, required=True)
    parser.add_argument("--unit-key", action="append", help="Run only a selected public unit key; may be repeated.")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--max-tokens", type=int, default=8192)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument(
        "--reasoning-effort",
        default="none",
        help="OpenRouter reasoning effort override; use 'none' for schema-bound JSON proof-lane runs.",
    )
    parser.add_argument("--max-tasks-per-call", type=int, default=1)
    parser.add_argument("--decline-context-pack", type=Path)
    parser.add_argument("--budget-only", action="store_true")
    parser.add_argument(
        "--resume-existing",
        action="store_true",
        help="Reuse completed batch generation-output.json files and call the provider only for missing batches.",
    )
    args = parser.parse_args()
    summary = run(args)
    print(json.dumps(summary, indent=2, sort_keys=True))
    if summary.get("provider_error_count"):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
