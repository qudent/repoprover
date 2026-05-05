#!/usr/bin/env python3
"""Generate Lean declarations for a LaTeX statement unit from hydrated context."""

from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from openai import OpenAI


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "deepseek/deepseek-v4-flash"


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: invalid JSON: {exc}") from exc
    return rows


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")


def public_source_unit(row: dict[str, Any]) -> dict[str, Any]:
    source = row["source_unit"]
    return {
        "id": row["id"],
        "environment": source["environment"],
        "path": source["path"],
        "line_range": source["line_range"],
        "labels": source.get("labels", []),
        "referenced_labels": source.get("referenced_labels", []),
        "part_markers": source.get("part_markers", []),
        "parse_warnings": source.get("parse_warnings", []),
        "source_text": source["source_text"],
    }


def load_selector_output(selector_run: Path) -> dict[str, Any]:
    output_path = selector_run / "batch-001" / "context-selection-output.json"
    if not output_path.exists():
        raise FileNotFoundError(output_path)
    return read_json(output_path)


def load_hydration(selector_run: Path) -> dict[str, Any]:
    hydration_path = selector_run / "batch-001" / "mathlib-lean-hydrated-context.json"
    if not hydration_path.exists():
        return {"hydrated_mathlib_context": [], "lean_check_status": "missing"}
    return read_json(hydration_path)


def load_selected_units(selector_run: Path) -> list[dict[str, Any]]:
    selected_path = selector_run / "eval" / "selected-units.jsonl"
    if not selected_path.exists():
        raise FileNotFoundError(selected_path)
    return read_jsonl(selected_path)


def load_selector_prompt_units(selector_run: Path) -> dict[str, dict[str, Any]]:
    payload_path = selector_run / "batch-001" / "context-selection-payload.json"
    if not payload_path.exists():
        return {}
    payload = read_json(payload_path)
    messages = payload.get("messages") or []
    user_message = next((message for message in messages if message.get("role") == "user"), None)
    if not user_message:
        return {}
    try:
        user_payload = json.loads(str(user_message.get("content") or ""))
    except json.JSONDecodeError:
        return {}
    return {str(unit.get("unit_key") or ""): unit for unit in user_payload.get("units") or []}


def units_by_public_key(selected_units: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {f"unit-{index + 1:03d}": row for index, row in enumerate(selected_units)}


def hydrated_for_task(hydration: dict[str, Any], *, unit_key: str, task_id: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in hydration.get("hydrated_mathlib_context") or []:
        if item.get("unit_key") == unit_key and item.get("task_id") == task_id:
            row = dict(item)
            lean_status = (row.get("lean_check") or {}).get("status")
            if lean_status == "checked":
                row["usage_policy"] = "checked_signature_authoritative"
            elif row.get("exact_identifier"):
                row["usage_policy"] = (
                    "exact_identifier_failed_lean_check_do_not_use; "
                    "fallback_mathlib_candidates are search hints, not checked facts"
                )
            else:
                row["usage_policy"] = "not_exact_identifier; use only as a search hint"
            rows.append(row)
    return rows


def build_generation_messages(selector_run: Path) -> list[dict[str, str]]:
    selector = load_selector_output(selector_run)
    hydration = load_hydration(selector_run)
    selected_units = load_selected_units(selector_run)
    selected_by_key = units_by_public_key(selected_units)
    prompt_units_by_key = load_selector_prompt_units(selector_run)

    units_payload: list[dict[str, Any]] = []
    for unit in selector.get("units") or []:
        unit_key = str(unit.get("unit_key") or "")
        source_row = selected_by_key.get(unit_key)
        if source_row is None:
            continue
        prompt_unit = prompt_units_by_key.get(unit_key, {})
        planned_tasks: list[dict[str, Any]] = []
        for task in unit.get("planned_declarations") or []:
            task_id = str(task.get("task_id") or "")
            planned_tasks.append(
                {
                    "task_id": task_id,
                    "kind": task.get("kind"),
                    "source_part": task.get("source_part"),
                    "selector_unchecked_statement_sketch": task.get("target_statement_sketch"),
                    "selector_sketch_warning": (
                        "This selector sketch is mathematical intent only. Do not copy its Lean syntax "
                        "or argument order verbatim; Lean-checked hydrated signatures are authoritative."
                    ),
                    "needed_source_context": task.get("needed_source_context", []),
                    "needed_project_context": task.get("needed_project_context", []),
                    "available_prior_project_context": prompt_unit.get("prior_project_context", []),
                    "local_file_predecessor_declarations": prompt_unit.get(
                        "local_file_predecessor_declarations", []
                    ),
                    "hydrated_mathlib_context": hydrated_for_task(hydration, unit_key=unit_key, task_id=task_id),
                    "missing_or_uncertain_context": task.get("missing_or_uncertain_context", []),
                }
            )
        units_payload.append(
            {
                "unit_key": unit_key,
                "source_unit": public_source_unit(source_row),
                "previous_source_context": prompt_unit.get("previous_source_context", []),
                "local_file_context_candidates": prompt_unit.get("local_file_context_candidates", []),
                "source_focus_summary": unit.get("source_focus_summary"),
                "formalization_risks": unit.get("formalization_risks", []),
                "planned_declarations": planned_tasks,
                "context_pack_size_risk": unit.get("context_pack_size_risk"),
                "selector_confidence": unit.get("selector_confidence"),
            }
        )

    system = (
        "You are a Lean 4 autoformalization agent. Generate a small ordered "
        "sequence of Lean declarations for the provided LaTeX theorem-like unit. "
        "Use only the source text, selector plan, previous-project context if "
        "shown, and Lean-checked Mathlib signatures in the prompt. The original "
        "aligned Lean declarations, names, statements, and proofs are withheld. "
        "Return exactly one JSON object."
    )
    user = {
        "task": (
            "Produce Lean declarations for each planned declaration task. The output "
            "should be a small Lean file body, without imports, containing the ordered "
            "declarations needed for this one source unit."
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
                    "used_context": ["source/project/Mathlib facts actually used"],
                    "notes": ["brief caveats or remaining uncertainty"],
                }
            ]
        },
        "instructions": [
            "Do not use sorry, admit, placeholders, or comments standing in for proof.",
            "Do not include import statements or markdown fences.",
            "Do not ask for or infer the hidden aligned Lean declaration names/statements/proofs.",
            "Treat selector_unchecked_statement_sketch as non-authoritative mathematical intent only; do not copy its Lean syntax verbatim.",
            "Follow the Lean-checked signatures exactly when they differ from the selector's expected shape.",
            "Use the actual Lean-checked argument order from hydrated_mathlib_context. If the selector expected shape conflicts with the checked signature, the checked signature wins.",
            "Never use a hydrated Mathlib exact_identifier whose lean_check.status is not `checked`; treat it as unavailable even if the selector expected it to exist.",
            "Treat fallback_mathlib_candidates as search hints only. Do not cite or use a fallback candidate as a theorem unless its statement in the prompt is sufficient for the proof.",
            "If a selected Mathlib API is field-specific, unit-specific, or otherwise not strong enough for the source statement, say so in notes and generate only declarations justified by the visible context.",
            "Do not invent project helper names that are not shown in available_prior_project_context, needed_project_context, or source context.",
            "When available_prior_project_context contains Lean snippets for project definitions or predicates, use those exact names and statement shapes instead of rephrasing the source with raw hypotheses.",
            "When local_file_predecessor_declarations contains same-file helper declarations, you may reuse those exact helper names and statement shapes; do not infer any hidden target declaration from their file position.",
            "Prefer a narrow declaration sequence over a broad bundled conjunction when the source unit decomposes into multiple Lean declarations.",
            "Keep theorem-local assumptions explicit rather than relying on unavailable global variables.",
            "If local_file_context_candidates show useful namespace, open, notation, or variable commands, you may include the needed commands in lean_file_body before the declarations.",
            "If you use a variable command instead of explicit binders, the command itself must appear in lean_file_body. Do not depend on file-scope variables that are not emitted in your output.",
            "Every identifier used in a theorem statement must be introduced by an explicit binder, local declaration, or imported/opened declaration. In particular, source parameters such as coefficient types, matrix sizes, rings, variables, and typeclass assumptions must be bound in the generated theorem, e.g. `{K : Type*} [CommRing K] {n : ℕ}` when the source quantifies over a commutative ring and a natural number.",
            "If you cannot produce a complete proof from visible context, set status to cannot_prove_from_visible_context and leave lean_file_body empty. Never output Lean containing sorry/admit/placeholders.",
        ],
        "lean_environment": {
            "toolchain": "leanprover/lean4:v4.28.0",
            "imports_available_in_verification_file": ["Mathlib"],
            "default_opens_used_for_context_hydration": hydration.get("opens", []),
        },
        "benchmark_policy": {
            "target_lean_available_to_generator": False,
            "posthoc_alignment_hidden": True,
            "gold_comparison_is_posthoc_only": True,
        },
        "units": units_payload,
    }
    return [{"role": "system", "content": system}, {"role": "user", "content": json.dumps(user, indent=2, sort_keys=True, ensure_ascii=False)}]


def extract_message_content(response: Any) -> str:
    try:
        return str(response.choices[0].message.content or "")
    except Exception:
        return ""


def maybe_parse_json(text: str) -> tuple[dict[str, Any] | None, str | None]:
    stripped = text.strip()
    if not stripped:
        return None, "empty_output"
    try:
        return json.loads(stripped), None
    except json.JSONDecodeError as exc:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(stripped[start : end + 1]), None
            except json.JSONDecodeError:
                pass
        return None, str(exc)


def response_cost_summary(response: Any, model: str) -> dict[str, Any]:
    usage = getattr(response, "usage", None)
    raw_usage = usage.model_dump() if hasattr(usage, "model_dump") else dict(usage or {})
    return {
        "model": model,
        "usage": raw_usage,
        "openrouter_reported_cost": raw_usage.get("cost"),
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    run_dir = args.output
    batch_dir = run_dir / "batch-001"
    eval_dir = run_dir / "eval"
    batch_dir.mkdir(parents=True, exist_ok=True)
    eval_dir.mkdir(parents=True, exist_ok=True)

    messages = build_generation_messages(args.selector_run)
    request_payload = {
        "model": args.model,
        "messages": messages,
        "temperature": args.temperature,
        "max_tokens": args.max_tokens,
        "response_format": {"type": "json_object"},
    }
    if args.reasoning_effort:
        request_payload["extra_body"] = {"reasoning": {"effort": args.reasoning_effort, "exclude": True}}
    write_json(batch_dir / "generation-payload.json", request_payload)

    summary: dict[str, Any] = {
        "schema_version": "repoprover.latex_statement_generation.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "selector_run": str(args.selector_run),
        "output_path": str(run_dir),
        "model": args.model,
        "reasoning_effort": args.reasoning_effort,
        "budget_only": args.budget_only,
        "paid_call_made": False,
        "valid_json": False,
        "parse_error": None,
    }
    if args.budget_only:
        write_json(eval_dir / "generation-results.json", summary)
        return summary

    if not os.getenv("OPENROUTER_API_KEY"):
        raise RuntimeError("OPENROUTER_API_KEY is not set")
    client = OpenAI(api_key=os.environ["OPENROUTER_API_KEY"], base_url=args.base_url)
    started = time.monotonic()
    response = client.chat.completions.create(**request_payload)
    summary["elapsed_seconds"] = round(time.monotonic() - started, 3)
    summary["paid_call_made"] = True
    write_json(batch_dir / "generation-response.json", response.model_dump())
    content = extract_message_content(response)
    (batch_dir / "generation-assistant-content.txt").write_text(content, encoding="utf-8")
    parsed, parse_error = maybe_parse_json(content)
    summary["parse_error"] = parse_error
    summary["valid_json"] = parsed is not None
    summary["cost_summary"] = response_cost_summary(response, args.model)
    if parsed is not None:
        write_json(batch_dir / "generation-output.json", parsed)
    write_json(eval_dir / "generation-results.json", summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selector-run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--max-tokens", type=int, default=4096)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument(
        "--reasoning-effort",
        default="none",
        help="OpenRouter reasoning effort override; use 'none' for schema-bound JSON generation.",
    )
    parser.add_argument("--budget-only", action="store_true")
    args = parser.parse_args()
    print(json.dumps(run(args), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
