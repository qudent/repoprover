#!/usr/bin/env python3
"""Build a checked repair context pack from repair-context selection output."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def load_selection(run_dir: Path) -> dict[str, Any]:
    path = run_dir / "batch-001" / "repair-context-selection-output.json"
    if not path.exists():
        raise FileNotFoundError(path)
    return read_json(path)


def load_hydration(run_dir: Path) -> dict[str, Any]:
    path = run_dir / "batch-001" / "mathlib-lean-hydrated-context.json"
    if not path.exists():
        raise FileNotFoundError(path)
    return read_json(path)


def mathlib_request_index(selection: dict[str, Any]) -> dict[tuple[str, int], dict[str, Any]]:
    index: dict[tuple[str, int], dict[str, Any]] = {}
    for unit in selection.get("units") or []:
        unit_key = str(unit.get("unit_key") or "")
        for request_index, request in enumerate(unit.get("needed_mathlib_context") or [], start=1):
            index[(unit_key, request_index)] = request
    return index


def build_context_pack(
    *,
    selection: dict[str, Any],
    hydration: dict[str, Any],
    repair_context_run: Path | None = None,
) -> dict[str, Any]:
    request_index = mathlib_request_index(selection)
    checked_signatures: list[dict[str, Any]] = []
    failed_or_unchecked: list[dict[str, Any]] = []

    for row in hydration.get("hydrated_mathlib_context") or []:
        unit_key = str(row.get("unit_key") or "")
        index = int(row.get("request_index") or 0)
        original = request_index.get((unit_key, index), {})
        lean_check = row.get("lean_check") or {}
        record = {
            "unit_key": unit_key,
            "task_id": row.get("task_id"),
            "name_or_query": row.get("query"),
            "exact_identifier": row.get("exact_identifier"),
            "expected_signature_or_shape": row.get("expected_signature_or_shape"),
            "why_needed": row.get("why_needed") or original.get("why_needed"),
            "lean_check": lean_check,
        }
        if lean_check.get("status") == "checked":
            checked_signatures.append(
                {
                    "unit_key": unit_key,
                    "task_id": row.get("task_id"),
                    "name": row.get("exact_identifier") or row.get("query"),
                    "signature": lean_check.get("signature"),
                    "why_needed": row.get("why_needed") or original.get("why_needed"),
                    "source": "autonomous_repair_context_selection_hydrated_with_lean_check",
                }
            )
        else:
            failed_or_unchecked.append(record)
            for candidate in (row.get("fallback_mathlib_candidates") or [])[:4]:
                candidate_check = candidate.get("lean_check") or {}
                if candidate_check.get("status") == "checked":
                    checked_signatures.append(
                        {
                            "unit_key": unit_key,
                            "task_id": row.get("task_id"),
                            "name": candidate.get("name"),
                            "signature": candidate_check.get("signature"),
                            "why_needed": (
                                f"Checked fallback candidate for failed request {row.get('query')}: "
                                f"{row.get('why_needed') or original.get('why_needed') or ''}"
                            ).strip(),
                            "source": "autonomous_repair_context_selection_checked_fallback_candidate",
                            "fallback_for_query": row.get("query"),
                            "declaration_line": candidate.get("declaration_line"),
                        }
                    )

    proof_strategy_notes: list[dict[str, Any]] = []
    selected_visible_context: list[dict[str, Any]] = []
    do_not_use_identifiers: list[str] = []
    missing_or_uncertain_context: list[dict[str, Any]] = []
    for unit in selection.get("units") or []:
        unit_key = str(unit.get("unit_key") or "")
        proof_strategy_notes.append(
            {
                "unit_key": unit_key,
                "failure_analysis": unit.get("failure_analysis"),
                "proof_strategy_note": unit.get("repair_strategy_note"),
                "selector_confidence": unit.get("selector_confidence"),
            }
        )
        for item in unit.get("selected_visible_context") or []:
            selected_visible_context.append({"unit_key": unit_key, **item})
        for name in unit.get("do_not_use_identifiers") or []:
            if name not in do_not_use_identifiers:
                do_not_use_identifiers.append(name)
        for item in unit.get("missing_or_uncertain_context") or []:
            missing_or_uncertain_context.append({"unit_key": unit_key, "item": item})

    return {
        "schema_version": "repoprover.latex_statement_checked_repair_context.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repair_context_run": str(repair_context_run) if repair_context_run else None,
        "benchmark_honesty_caveat": (
            "Autonomous second-round repair-context selector output. Hidden aligned target Lean "
            "declarations, statements, names, and proofs are not included. Mathlib signatures here "
            "are included only after Lean #check hydration."
        ),
        "proof_strategy_notes": proof_strategy_notes,
        "selected_visible_context": selected_visible_context,
        "checked_signatures": checked_signatures,
        "failed_or_unchecked_context_requests": failed_or_unchecked,
        "do_not_use_identifiers": do_not_use_identifiers,
        "missing_or_uncertain_context": missing_or_uncertain_context,
        "raw_selection_output": selection,
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    pack = build_context_pack(
        selection=load_selection(args.repair_context_run),
        hydration=load_hydration(args.repair_context_run),
        repair_context_run=args.repair_context_run,
    )
    write_json(args.output, pack)
    return {
        "schema_version": "repoprover.latex_statement_checked_repair_context_build.v1",
        "output": str(args.output),
        "checked_signature_count": len(pack["checked_signatures"]),
        "failed_or_unchecked_context_request_count": len(pack["failed_or_unchecked_context_requests"]),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repair-context-run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
