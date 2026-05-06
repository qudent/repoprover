#!/usr/bin/env python3
"""Build target-hidden proof-lane dossiers for theorem-level failures."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.run_latex_statement_generation import write_json  # noqa: E402
from scripts.run_latex_statement_generation_repair import load_generation_output  # noqa: E402


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")


def selector_run_for_generation_run(generation_run: Path) -> Path | None:
    for filename in ("generation-results.json", "repair-results.json", "merge-summary.json"):
        path = generation_run / "eval" / filename
        if not path.exists():
            continue
        try:
            data = read_json(path)
        except (OSError, json.JSONDecodeError):
            continue
        selector_run = str(data.get("selector_run") or "")
        if selector_run:
            return Path(selector_run)
    return None


def public_source_unit(row: dict[str, Any]) -> dict[str, Any]:
    source = row.get("source_unit") or {}
    return {
        "id": row.get("id"),
        "environment": source.get("environment"),
        "path": source.get("path"),
        "line_range": source.get("line_range"),
        "labels": source.get("labels", []),
        "referenced_labels": source.get("referenced_labels", []),
        "part_markers": source.get("part_markers", []),
        "parse_warnings": source.get("parse_warnings", []),
        "source_text": source.get("source_text"),
    }


def selected_units_by_key(selector_run: Path | None) -> dict[str, dict[str, Any]]:
    if selector_run is None:
        return {}
    rows = read_jsonl(selector_run / "eval" / "selected-units.jsonl")
    return {f"unit-{index + 1:03d}": public_source_unit(row) for index, row in enumerate(rows)}


def user_payload(path: Path) -> dict[str, Any]:
    try:
        payload = read_json(path)
    except (OSError, json.JSONDecodeError):
        return {}
    for message in payload.get("messages") or []:
        if message.get("role") != "user":
            continue
        content = message.get("content")
        if not isinstance(content, str):
            continue
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return {}
    return {}


def generation_payload_paths(run_dir: Path) -> list[Path]:
    return sorted(run_dir.glob("batch-*/generation-payload.json"))


def units_from_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
    if isinstance(payload.get("units"), list):
        return list(payload["units"])
    if isinstance(payload.get("proof_lane_tasks"), list):
        return list(payload["proof_lane_tasks"])
    original = payload.get("original_generation_task")
    if isinstance(original, dict) and isinstance(original.get("units"), list):
        return list(original["units"])
    return []


def prompt_unit_by_key(run_dir: Path) -> dict[str, dict[str, Any]]:
    units: dict[str, dict[str, Any]] = {}
    for path in generation_payload_paths(run_dir):
        payload = user_payload(path)
        for unit in units_from_payload(payload):
            unit_key = str(unit.get("unit_key") or "")
            if unit_key and unit_key not in units:
                units[unit_key] = unit
    return units


def verification_units_by_key(verification: dict[str, Any]) -> dict[str, dict[str, Any]]:
    units: dict[str, dict[str, Any]] = {}
    for batch in verification.get("batches") or []:
        for unit in batch.get("units") or []:
            unit_key = str(unit.get("unit_key") or "")
            if unit_key:
                units[unit_key] = unit
    return units


def semantic_units_by_key(semantic: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not semantic:
        return {}
    return {
        str(unit.get("unit_key") or ""): unit
        for unit in semantic.get("units") or []
        if unit.get("unit_key")
    }


def compact_semantic_unit(unit: dict[str, Any] | None) -> dict[str, Any] | None:
    if not unit:
        return None
    return {
        "unit_key": unit.get("unit_key"),
        "source_unit_id": unit.get("source_unit_id"),
        "compile_passed": unit.get("compile_passed"),
        "coverage_status": unit.get("coverage_status"),
        "compile_gate_bypassed": unit.get("compile_gate_bypassed"),
    }


def compact_verification_unit(unit: dict[str, Any]) -> dict[str, Any]:
    return {
        "unit_key": unit.get("unit_key"),
        "compile_passed": unit.get("compile_passed"),
        "failure_class": unit.get("failure_class"),
        "reported_status": unit.get("reported_status"),
        "skipped_reason": unit.get("skipped_reason"),
        "contract_violations": unit.get("contract_violations") or [],
        "messages": unit.get("messages") or [],
        "visible_support_context": unit.get("visible_support_context") or {},
    }


def selected_context_from_prompt_unit(unit: dict[str, Any]) -> dict[str, Any]:
    if isinstance(unit.get("visible_prompt_context"), dict) and not unit.get("planned_declarations"):
        return selected_context_from_prompt_unit(unit["visible_prompt_context"])
    tasks: list[dict[str, Any]] = []
    for task in unit.get("planned_declarations") or []:
        tasks.append(
            {
                "task_id": task.get("task_id"),
                "kind": task.get("kind"),
                "role": task.get("role"),
                "source_part": task.get("source_part"),
                "depends_on_task_ids": task.get("depends_on_task_ids", []),
                "selector_unchecked_statement_sketch": task.get("selector_unchecked_statement_sketch"),
                "needed_source_context": task.get("needed_source_context", []),
                "needed_project_context": task.get("needed_project_context", []),
                "available_prior_project_context": task.get("available_prior_project_context", []),
                "local_file_predecessor_declarations": task.get("local_file_predecessor_declarations", []),
                "hydrated_mathlib_context": task.get("hydrated_mathlib_context", []),
                "missing_or_uncertain_context": task.get("missing_or_uncertain_context", []),
            }
        )
    return {
        "previous_source_context": unit.get("previous_source_context", []),
        "local_file_context_candidates": unit.get("local_file_context_candidates", []),
        "source_focus_summary": unit.get("source_focus_summary"),
        "formalization_risks": unit.get("formalization_risks", []),
        "planned_declarations": tasks,
        "additional_checked_repair_context": unit.get("additional_checked_repair_context", []),
    }


def markdown_for_task(task: dict[str, Any]) -> str:
    source = task.get("source_unit") or {}
    verification = task.get("verification") or {}
    current = task.get("current_generation") or {}
    notes = current.get("notes") or []
    return "\n".join(
        [
            f"# Proof-Lane Task {task['unit_key']}",
            "",
            "## Policy",
            "Use only the visible source/context below. Do not inspect or infer hidden aligned Lean target declarations.",
            "",
            "## Source",
            f"- ID: `{source.get('id')}`",
            f"- Path: `{source.get('path')}`",
            f"- Labels: `{', '.join(source.get('labels') or [])}`",
            "",
            "```tex",
            str(source.get("source_text") or ""),
            "```",
            "",
            "## Current Outcome",
            f"- Generation status: `{current.get('status')}`",
            f"- Verification failure class: `{verification.get('failure_class')}`",
            f"- Reported status: `{verification.get('reported_status')}`",
            "",
            "## Model Notes",
            *[f"- {note}" for note in notes],
            "",
            "## Task",
            "Try to produce complete Lean declarations from the visible context. If the context is still insufficient, record the missing checked facts precisely.",
        ]
    ) + "\n"


def build_tasks(args: argparse.Namespace) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    selector_run = args.selector_run or selector_run_for_generation_run(args.generation_run)
    source_units = selected_units_by_key(selector_run)
    generation = load_generation_output(args.generation_run)
    generation_units = {str(unit.get("unit_key") or ""): unit for unit in generation.get("units") or []}
    verification = read_json(args.verification_results)
    verification_units = verification_units_by_key(verification)
    semantic = read_json(args.semantic_coverage) if args.semantic_coverage and args.semantic_coverage.exists() else None
    semantic_units = semantic_units_by_key(semantic)
    prompt_units = prompt_unit_by_key(args.generation_run)
    allowed_keys = set(args.unit_key or [])

    tasks: list[dict[str, Any]] = []
    for unit_key, verification_unit in sorted(verification_units.items()):
        if allowed_keys and unit_key not in allowed_keys:
            continue
        if verification_unit.get("failure_class") not in set(args.failure_class):
            continue
        generation_unit = generation_units.get(unit_key, {})
        task = {
            "schema_version": "repoprover.latex_statement_proof_lane_task.v1",
            "unit_key": unit_key,
            "source_unit": source_units.get(unit_key, {}),
            "current_generation": generation_unit,
            "verification": compact_verification_unit(verification_unit),
            "semantic_coverage": compact_semantic_unit(semantic_units.get(unit_key)),
            "visible_prompt_context": selected_context_from_prompt_unit(prompt_units.get(unit_key, {})),
            "benchmark_policy": {
                "target_lean_available_to_proof_lane": False,
                "posthoc_alignment_hidden": True,
                "gold_comparison_is_posthoc_only": True,
            },
            "instructions": [
                "Do not inspect hidden aligned target Lean declarations or post-hoc gold metadata.",
                "Use source text, previous source/project/local context, checked Mathlib signatures, and verifier-visible support only.",
                "If a proof succeeds, output a normal generation-output.json unit that can be overlaid with scripts/merge_latex_statement_generation_units.py.",
                "If proof still fails, report the missing checked project/local/Mathlib facts precisely.",
            ],
        }
        tasks.append(task)

    summary = {
        "schema_version": "repoprover.latex_statement_proof_lane_tasks.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generation_run": str(args.generation_run),
        "verification_results": str(args.verification_results),
        "semantic_coverage": str(args.semantic_coverage) if args.semantic_coverage else None,
        "selector_run": str(selector_run) if selector_run else None,
        "failure_classes": list(args.failure_class),
        "unit_count": len(tasks),
        "unit_keys": [task["unit_key"] for task in tasks],
        "benchmark_policy": {
            "target_lean_available_to_proof_lane": False,
            "posthoc_alignment_hidden": True,
            "gold_comparison_is_posthoc_only": True,
        },
    }
    return tasks, summary


def run(args: argparse.Namespace) -> dict[str, Any]:
    tasks, summary = build_tasks(args)
    args.output.mkdir(parents=True, exist_ok=True)
    write_jsonl(args.output / "proof-lane-tasks.jsonl", tasks)
    write_json(args.output / "proof-lane-summary.json", summary)
    tasks_dir = args.output / "tasks"
    for task in tasks:
        write_json(tasks_dir / f"{task['unit_key']}.json", task)
        (tasks_dir / f"{task['unit_key']}.md").write_text(markdown_for_task(task), encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--generation-run", type=Path, required=True)
    parser.add_argument("--verification-results", type=Path, required=True)
    parser.add_argument("--semantic-coverage", type=Path)
    parser.add_argument("--selector-run", type=Path)
    parser.add_argument("--failure-class", action="append", default=["declined_cannot_prove"])
    parser.add_argument("--unit-key", action="append")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
