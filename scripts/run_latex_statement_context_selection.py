#!/usr/bin/env python3
"""Run context selection on LaTeX-statement units.

This is the theorem-level counterpart to ``run_source_context_selection.py``.
It takes rows from ``docs/latex-statement-gold-candidates.jsonl`` and asks a
model to produce an ordered declaration plan plus separate source/project/
Mathlib context requests.

Target Lean alignments for the selected unit are withheld from the prompt. Prior
source references may expose already-formalized project declarations when they
belong to earlier/referenced source units.
"""

from __future__ import annotations

import argparse
import json
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from openai import OpenAI


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "deepseek/deepseek-v4-flash"


@dataclass(frozen=True)
class SelectedUnit:
    public_key: str
    row: dict[str, Any]


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


def select_units(rows: list[dict[str, Any]], limit: int) -> list[SelectedUnit]:
    selected: list[SelectedUnit] = []
    for row in rows:
        if row.get("selection", {}).get("status") != "gold_candidate":
            continue
        selected.append(SelectedUnit(public_key=f"unit-{len(selected) + 1:03d}", row=row))
        if limit and len(selected) >= limit:
            break
    if not selected:
        raise ValueError("no LaTeX statement gold candidates selected")
    return selected


def unit_index(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(row["id"]): row for row in rows}


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
        "source_text": source["source_text"],
        "parse_warnings": source.get("parse_warnings", []),
    }


def declaration_stub(decl: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": decl["full_name"],
        "kind": decl["kind"],
        "path": decl["path"],
        "line_range": decl["line_range"],
        "declared_source_labels": decl.get("declared_source_labels", []),
    }


def prior_project_context(row: dict[str, Any], rows_by_id: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    contexts: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    candidate_refs = []
    candidate_refs.extend(row.get("context_candidates", {}).get("referenced_source_units", []))
    candidate_refs.extend(row.get("context_candidates", {}).get("previous_same_file_source_units", []))

    for ref in candidate_refs:
        unit_id = ref.get("unit_id")
        if not unit_id:
            continue
        prior = rows_by_id.get(str(unit_id))
        if prior is None:
            continue
        aligned = prior.get("posthoc_lean_alignment", {}).get("aligned_lean_declarations", [])
        declarations = []
        for decl in aligned[:12]:
            key = (decl["path"], decl["full_name"])
            if key in seen:
                continue
            declarations.append(declaration_stub(decl))
            seen.add(key)
        if declarations:
            contexts.append(
                {
                    "source_unit_id": prior["id"],
                    "source_labels": prior["source_unit"].get("labels", []),
                    "reason": "Earlier or explicitly referenced source unit with post-hoc project declarations.",
                    "project_declarations": declarations,
                }
            )
    return contexts


def build_messages(selected: list[SelectedUnit], all_rows: list[dict[str, Any]]) -> list[dict[str, str]]:
    rows_by_id = unit_index(all_rows)
    system = (
        "You are a Lean 4/Mathlib context-planning agent. Prepare a compact "
        "context pack for formalizing a LaTeX theorem-like source unit. The "
        "target Lean declarations aligned to the selected source unit are "
        "withheld. Return exactly one JSON object."
    )
    payload = {
        "task": (
            "For each LaTeX source unit, decompose the source into ordered Lean "
            "declaration tasks and select tight context for each task. The "
            "context inventory must be separate: source text, previous book/source "
            "statements, previous project declarations, local file/import/style "
            "context, and selected Mathlib APIs."
        ),
        "schema": {
            "units": [
                {
                    "unit_key": "unit-001",
                    "source_focus_summary": "short summary",
                    "formalization_risks": ["source ambiguity, missing notation, broad multi-part theorem"],
                    "planned_declarations": [
                        {
                            "task_id": "unit-001-task-1",
                            "kind": "def|theorem|lemma|instance|notation|unknown",
                            "source_part": "whole unit or part marker",
                            "target_statement_sketch": "mathematical Lean-shape sketch, not exact hidden Lean",
                            "needed_source_context": ["source labels/statements"],
                            "needed_project_context": [
                                {
                                    "name": "previous project declaration if provided or likely needed",
                                    "why_needed": "supporting theorem/definition/notation",
                                }
                            ],
                            "needed_mathlib_context": [
                                {
                                    "name_or_query": "exact Mathlib name or narrow search query",
                                    "expected_signature_or_shape": "expected type/signature/docstring",
                                    "why_needed": "definition/proof/tactic support",
                                }
                            ],
                            "missing_or_uncertain_context": ["what a second lookup round should resolve"],
                        }
                    ],
                    "context_pack_size_risk": "low|medium|high",
                    "selector_confidence": 0.0,
                }
            ]
        },
        "rules": [
            "Do not infer or reveal hidden target Lean declaration names for the selected unit.",
            "Do not bundle all source parts into one conjunction unless the source unit itself requires that shape.",
            "Use previous project declarations only if they are shown under prior_project_context.",
            "Do not treat Mathlib as the only context; enumerate source/project/local/Mathlib context separately.",
            "Prefer exact Mathlib names when known; otherwise give a narrow query plus expected signature shape.",
            "Keep added context tight: prefer a few thousand tokens or less per source unit.",
        ],
        "units": [],
    }

    for item in selected:
        row = item.row
        payload["units"].append(
            {
                "unit_key": item.public_key,
                "source_unit": public_source_unit(row),
                "source_context_candidates": row.get("context_candidates", {}),
                "prior_project_context": prior_project_context(row, rows_by_id),
                "benchmark_policy": {
                    "target_lean_available_to_selector": False,
                    "posthoc_alignment_hidden": True,
                },
            }
        )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False)},
    ]


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
    rows = read_jsonl(args.records)
    selected = select_units(rows, args.limit)
    messages = build_messages(selected, rows)
    run_dir = args.output
    batch_dir = run_dir / "batch-001"
    eval_dir = run_dir / "eval"
    batch_dir.mkdir(parents=True, exist_ok=True)
    eval_dir.mkdir(parents=True, exist_ok=True)

    request_payload: dict[str, Any] = {
        "model": args.model,
        "messages": messages,
        "temperature": args.temperature,
        "max_tokens": args.max_tokens,
        "response_format": {"type": "json_object"},
    }
    write_json(batch_dir / "context-selection-payload.json", request_payload)
    write_jsonl(eval_dir / "selected-units.jsonl", [item.row for item in selected])

    summary: dict[str, Any] = {
        "schema_version": "repoprover.latex_statement_context_selection.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "records_input": len(rows),
        "units_selected": len(selected),
        "model": args.model,
        "budget_only": args.budget_only,
        "paid_call_made": False,
        "valid_json": False,
        "parse_error": None,
        "output_path": str(run_dir),
    }

    if args.budget_only:
        write_json(eval_dir / "context-selection-results.json", summary)
        return summary

    if not os.getenv("OPENROUTER_API_KEY"):
        raise RuntimeError("OPENROUTER_API_KEY is not set")
    client = OpenAI(api_key=os.environ["OPENROUTER_API_KEY"], base_url=args.base_url)
    started = time.monotonic()
    response = client.chat.completions.create(**request_payload)
    summary["elapsed_seconds"] = round(time.monotonic() - started, 3)
    summary["paid_call_made"] = True
    write_json(batch_dir / "context-selection-response.json", response.model_dump())
    content = extract_message_content(response)
    (batch_dir / "context-selection-assistant-content.txt").write_text(content, encoding="utf-8")
    parsed, parse_error = maybe_parse_json(content)
    summary["parse_error"] = parse_error
    summary["valid_json"] = parsed is not None
    summary["cost_summary"] = response_cost_summary(response, args.model)
    if parsed is not None:
        write_json(batch_dir / "context-selection-output.json", parsed)
    write_json(eval_dir / "context-selection-results.json", summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", type=Path, default=REPO_ROOT / "docs/latex-statement-gold-candidates.jsonl")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=1)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--max-tokens", type=int, default=4096)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--budget-only", action="store_true")
    args = parser.parse_args()

    print(json.dumps(run(args), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
