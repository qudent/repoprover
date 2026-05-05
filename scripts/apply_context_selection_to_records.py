#!/usr/bin/env python3
"""Apply context-selection outputs to source-statement records.

This consumes a successful `run_source_context_selection.py` run and writes a
new records JSONL where `minimal_context.mathlib_context` is augmented with the
selector's requested Mathlib APIs, resolved snippets, and proof notes. It does
not read or use `gold-comparison.json`.
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.materialize_minimal_context_smoke import load_jsonl  # noqa: E402
from scripts.run_minimal_context_eval import write_json, write_jsonl  # noqa: E402


def load_selection_outputs(run: Path) -> dict[str, dict[str, Any]]:
    selections: dict[str, dict[str, Any]] = {}
    for output_path in sorted(run.glob("batch-*/context-selection-output.json")):
        payload = json.loads(output_path.read_text(encoding="utf-8"))
        for row in payload.get("records") or []:
            key = str(row.get("record_key") or "")
            if key:
                selections[key] = row
    return selections


def load_hydrated_outputs(run: Path) -> dict[str, list[dict[str, Any]]]:
    hydrated: dict[str, list[dict[str, Any]]] = {}
    for output_path in sorted(run.glob("batch-*/mathlib-hydrated-context.json")):
        payload = json.loads(output_path.read_text(encoding="utf-8"))
        for row in payload.get("records") or []:
            key = str(row.get("record_key") or "")
            if key:
                hydrated[key] = list(row.get("resolved_mathlib_context") or [])
    return hydrated


def selected_candidate_summary(selection: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for item in selection.get("candidate_mathlib_context") or []:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        if not name:
            continue
        shape = str(item.get("expected_signature_or_shape") or "").strip()
        why = str(item.get("why_needed") or "").strip()
        confidence = item.get("confidence")
        parts = [f"`{name}`"]
        if shape:
            parts.append(f"shape: {shape}")
        if why:
            parts.append(f"why: {why}")
        if confidence is not None:
            parts.append(f"confidence: {confidence}")
        lines.append("; ".join(parts))
    return lines


def selected_project_context_summary(selection: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for item in selection.get("candidate_project_context") or []:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        if not name:
            continue
        shape = str(item.get("expected_signature_or_shape") or "").strip()
        why = str(item.get("why_needed") or "").strip()
        confidence = item.get("confidence")
        parts = [f"`{name}`"]
        if shape:
            parts.append(f"shape: {shape}")
        if why:
            parts.append(f"why: {why}")
        if confidence is not None:
            parts.append(f"confidence: {confidence}")
        lines.append("; ".join(parts))
    return lines


def hydrate_snippet_lines(resolved: list[dict[str, Any]], *, max_chars: int) -> list[str]:
    lines: list[str] = []
    used_chars = 0
    for query in resolved:
        query_text = str(query.get("query") or "")
        matches = list(query.get("matches") or [])
        if not matches:
            lines.append(f"Mathlib query `{query_text}` returned no local source match.")
            continue
        for match in matches[:2]:
            snippet = str(match.get("snippet") or match.get("text") or "").strip()
            if not snippet:
                continue
            header = f"Mathlib source match for `{query_text}` at {match.get('file')}:{match.get('line')}:"
            block = f"{header}\n```lean\n{snippet}\n```"
            if used_chars + len(block) > max_chars:
                lines.append(f"Mathlib context truncated after {used_chars} characters for context budget.")
                return lines
            lines.append(block)
            used_chars += len(block)
    return lines


def context_selection_lines(selection: dict[str, Any], hydrated: list[dict[str, Any]], *, max_hydrated_chars: int) -> list[str]:
    lines = [
        "Context-selection output; generated from source-only prompt before any gold comparison.",
    ]
    summary = str(selection.get("source_focus_summary") or "").strip()
    if summary:
        lines.append(f"Source focus: {summary}")
    selected_part = str(selection.get("selected_source_part") or "").strip()
    if selected_part:
        lines.append(f"Selected source part: {selected_part}")
    part_rationale = str(selection.get("source_part_rationale") or "").strip()
    if part_rationale:
        lines.append(f"Source-part rationale: {part_rationale}")
    boundary = str(selection.get("supporting_context_boundary") or "").strip()
    if boundary:
        lines.append(f"Supporting context boundary: {boundary}")
    sketch = [str(item).strip() for item in selection.get("formalization_sketch") or [] if str(item).strip()]
    if sketch:
        lines.append("Formalization sketch:")
        lines.extend(f"- {item}" for item in sketch)
    candidates = selected_candidate_summary(selection)
    if candidates:
        lines.append("Selected candidate Mathlib/API context:")
        lines.extend(f"- {item}" for item in candidates)
    project_candidates = selected_project_context_summary(selection)
    if project_candidates:
        lines.append("Selected candidate previous project context:")
        lines.extend(f"- {item}" for item in project_candidates)
    proof_notes = [str(item).strip() for item in selection.get("proof_notes") or [] if str(item).strip()]
    if proof_notes:
        lines.append("Proof notes:")
        lines.extend(f"- {item}" for item in proof_notes)
    uncertainties = [str(item).strip() for item in selection.get("uncertainties") or [] if str(item).strip()]
    if uncertainties:
        lines.append("Uncertainties to resolve during repair/review:")
        lines.extend(f"- {item}" for item in uncertainties)
    hydrated_lines = hydrate_snippet_lines(hydrated, max_chars=max_hydrated_chars)
    if hydrated_lines:
        lines.append("Hydrated Mathlib source snippets:")
        lines.extend(hydrated_lines)
    return lines


def apply_context_selection(args: argparse.Namespace) -> dict[str, Any]:
    records_path = args.records or args.context_selection_run / "eval" / "selected-records.jsonl"
    records = load_jsonl(records_path)
    selections = load_selection_outputs(args.context_selection_run)
    hydrated = load_hydrated_outputs(args.context_selection_run)
    output_rows: list[dict[str, Any]] = []
    missing_selection: list[str] = []

    for index, row in enumerate(records, start=1):
        key = f"record-{index:03d}"
        selection = selections.get(key)
        if selection is None:
            missing_selection.append(key)
            if not args.keep_missing:
                continue
            output_rows.append(row)
            continue
        updated = copy.deepcopy(row)
        minimal_context = updated.setdefault("minimal_context", {})
        existing = [str(item) for item in minimal_context.get("mathlib_context") or []]
        selected_lines = context_selection_lines(
            selection,
            hydrated.get(key, []),
            max_hydrated_chars=args.max_hydrated_chars_per_record,
        )
        minimal_context["mathlib_context"] = [*existing, *selected_lines]
        minimal_context["context_selection"] = {
            "source_run": str(args.context_selection_run),
            "record_key": key,
            "applied_at": datetime.now(timezone.utc).isoformat(),
            "used_gold_comparison": False,
            "selector_model": args.selector_model,
        }
        output_rows.append(updated)

    write_jsonl(args.output, output_rows)
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "context_selection_run": str(args.context_selection_run),
        "records_input": len(records),
        "records_output": len(output_rows),
        "records_missing_selection": missing_selection,
        "output": str(args.output),
        "used_gold_comparison": False,
    }
    if args.report_output:
        write_json(args.report_output, summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--context-selection-run", type=Path, required=True)
    parser.add_argument("--records", type=Path, default=None)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report-output", type=Path, default=None)
    parser.add_argument("--selector-model", default=None)
    parser.add_argument("--max-hydrated-chars-per-record", type=int, default=8000)
    parser.add_argument("--keep-missing", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    print(json.dumps(apply_context_selection(parse_args()), indent=2))
