#!/usr/bin/env python3
"""Select higher-trust candidates from whole-corpus minimal-context records.

The whole-corpus generator intentionally emits complete but mixed-trust records.
This script makes the next review surface explicit: records with exact Lean
doc-comment source alignment, valid file spans, and bounded context size. It is
still not a human-certification pass; selected rows remain gold candidates.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SELECTOR_VERSION = "gold-candidate-filter-v1"


@dataclass(frozen=True)
class SelectionConfig:
    max_source_lines: int = 80
    max_output_lines: int = 50
    max_lean_predecessors: int = 10
    require_source_method: str = "lean_comment_label"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: invalid JSON: {exc}") from exc
    return records


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, sort_keys=True, ensure_ascii=False) + "\n")


def span_length(line_range: list[int] | tuple[int, int]) -> int:
    start, end = line_range
    return int(end) - int(start) + 1


def total_source_lines(record: dict[str, Any]) -> int:
    return sum(span_length(span["line_range"]) for span in record["minimal_context"].get("source_spans", []))


def output_lines(record: dict[str, Any]) -> int:
    return span_length(record["output"]["line_range"])


class SpanValidator:
    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root
        self._line_counts: dict[str, int | None] = {}

    def line_count(self, relative_path: str) -> int | None:
        if relative_path not in self._line_counts:
            path = self.project_root / relative_path
            if not path.exists():
                self._line_counts[relative_path] = None
            else:
                self._line_counts[relative_path] = max(1, len(path.read_text(encoding="utf-8").splitlines()))
        return self._line_counts[relative_path]

    def validate_span(self, relative_path: str, line_range: list[int] | tuple[int, int]) -> str | None:
        line_count = self.line_count(relative_path)
        if line_count is None:
            return "missing_path"
        start, end = [int(value) for value in line_range]
        if start < 1 or end < start or end > line_count:
            return "invalid_line_range"
        return None


def rejection_reasons(
    record: dict[str, Any],
    config: SelectionConfig,
    validator: SpanValidator | None = None,
) -> list[str]:
    reasons: list[str] = []
    source_spans = record["minimal_context"].get("source_spans", [])
    lean_predecessors = record["minimal_context"].get("lean_predecessors", [])

    if record["alignment"].get("source_method") != config.require_source_method:
        reasons.append(f"source_method_not_{config.require_source_method}")
    if not source_spans:
        reasons.append("missing_source_span")
    if any(span.get("method") != config.require_source_method for span in source_spans):
        reasons.append("source_span_method_mismatch")
    if any(not span.get("labels") for span in source_spans):
        reasons.append("source_span_missing_label")
    if total_source_lines(record) > config.max_source_lines:
        reasons.append("source_span_too_large")
    if output_lines(record) > config.max_output_lines:
        reasons.append("output_span_too_large")
    if len(lean_predecessors) > config.max_lean_predecessors:
        reasons.append("too_many_lean_predecessors")

    if validator is not None:
        output_error = validator.validate_span(record["output"]["lean_path"], record["output"]["line_range"])
        if output_error:
            reasons.append(f"output_{output_error}")
        for span in source_spans:
            source_error = validator.validate_span(span["path"], span["line_range"])
            if source_error:
                reasons.append(f"source_{source_error}")
        for predecessor in lean_predecessors:
            predecessor_error = validator.validate_span(predecessor["path"], predecessor["line_range"])
            if predecessor_error:
                reasons.append(f"predecessor_{predecessor_error}")

    return sorted(set(reasons))


def annotate_selected_record(record: dict[str, Any], config: SelectionConfig, selected_at: str) -> dict[str, Any]:
    annotated = deepcopy(record)
    annotated["selection"] = {
        "selector_version": SELECTOR_VERSION,
        "selected_at": selected_at,
        "status": "gold_candidate",
        "criteria": {
            "source_method": config.require_source_method,
            "max_source_lines": config.max_source_lines,
            "max_output_lines": config.max_output_lines,
            "max_lean_predecessors": config.max_lean_predecessors,
            "validated_file_line_spans": True,
        },
        "caveat": "Deterministic high-trust filter only; not human-certified gold.",
    }
    notes = list(annotated.get("review_notes", []))
    note = "Selected by deterministic high-trust filter; still needs human or adversarial model review for gold use."
    if note not in notes:
        notes.append(note)
    annotated["review_notes"] = notes
    return annotated


def select_records(
    records: list[dict[str, Any]],
    config: SelectionConfig,
    validator: SpanValidator | None = None,
    selected_at: str | None = None,
) -> tuple[list[dict[str, Any]], Counter[str], Counter[str]]:
    selected_at = selected_at or datetime.now(timezone.utc).isoformat()
    selected: list[dict[str, Any]] = []
    reason_counts: Counter[str] = Counter()
    method_counts: Counter[str] = Counter()

    for record in records:
        method_counts[record["alignment"].get("source_method", "unknown")] += 1
        reasons = rejection_reasons(record, config, validator)
        if reasons:
            reason_counts.update(reasons)
            continue
        selected.append(annotate_selected_record(record, config, selected_at))

    return selected, reason_counts, method_counts


def report_markdown(
    *,
    input_path: Path,
    output_path: Path,
    records: list[dict[str, Any]],
    selected: list[dict[str, Any]],
    reason_counts: Counter[str],
    method_counts: Counter[str],
    config: SelectionConfig,
    elapsed_seconds: float,
) -> str:
    selected_kind_counts = Counter(row["output"]["chunk_kind"] for row in selected)
    selected_method_counts = Counter(row["alignment"]["source_method"] for row in selected)
    selected_chapter_counts = Counter(row.get("chapter_id") or "missing_chapter_id" for row in selected)
    top_chapters = selected_chapter_counts.most_common(12)

    payload = {
        "input_records": len(records),
        "selected_records": len(selected),
        "rejected_records": len(records) - len(selected),
        "selection_rate": round(len(selected) / len(records), 6) if records else 0.0,
        "criteria": {
            "source_method": config.require_source_method,
            "max_source_lines": config.max_source_lines,
            "max_output_lines": config.max_output_lines,
            "max_lean_predecessors": config.max_lean_predecessors,
        },
        "source_methods": dict(sorted(method_counts.items())),
        "selected_kinds": dict(sorted(selected_kind_counts.items())),
        "selected_source_methods": dict(sorted(selected_method_counts.items())),
        "top_selected_chapters": top_chapters,
        "rejection_reasons": dict(sorted(reason_counts.items())),
        "elapsed_seconds": round(elapsed_seconds, 3),
        "model_cost_usd": 0.0,
    }

    lines = [
        "# Minimal Context Gold Candidate Filter Report",
        "",
        "Generated by `scripts/filter_minimal_context_gold_candidates.py`.",
        "",
        "## Hypothesis",
        "",
        "Exact Lean doc-comment references to TeX labels form a better first gold-candidate surface than manifest-position fallbacks. Bounded source, output, and predecessor sizes keep records cheap enough for adversarial review and RepoProver smokes.",
        "",
        "## Artifacts",
        "",
        f"- Input: `{input_path.as_posix()}`",
        f"- Selected JSONL: `{output_path.as_posix()}`",
        "- Model/API cost: `$0.00` (deterministic local filtering only)",
        "",
        "## Summary",
        "",
        "```json",
        json.dumps(payload, indent=2, sort_keys=True),
        "```",
        "",
        "## Trust Boundary",
        "",
        "Selected records are higher-trust candidates, not human-certified gold. They have exact source-label alignment and validated file/line spans, but Lean dependency context is still heuristic and should be checked before using the records as final labels.",
        "",
        "Skipped records remain in the full corpus artifact. The largest skipped groups are expected: manifest-position fallbacks, unmapped Lean files, and records whose source/output/predecessor context is too large for the first review pass.",
        "",
        "## Next Use",
        "",
        "Use this subset as the next adversarial-review queue or as the low-risk input for bounded RepoProver smokes. Keep rejected or ugly full-corpus records available as hard negatives.",
        "",
    ]
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("docs/minimal-context-full-records.jsonl"))
    parser.add_argument("--output", type=Path, default=Path("docs/minimal-context-gold-candidates.jsonl"))
    parser.add_argument("--report-output", type=Path, default=Path("docs/minimal-context-gold-candidates-report.md"))
    parser.add_argument("--project-root", type=Path, default=Path("algebraic-combinatorics"))
    parser.add_argument("--max-source-lines", type=int, default=SelectionConfig.max_source_lines)
    parser.add_argument("--max-output-lines", type=int, default=SelectionConfig.max_output_lines)
    parser.add_argument("--max-lean-predecessors", type=int, default=SelectionConfig.max_lean_predecessors)
    return parser.parse_args()


def main() -> None:
    started = datetime.now(timezone.utc)
    args = parse_args()
    config = SelectionConfig(
        max_source_lines=args.max_source_lines,
        max_output_lines=args.max_output_lines,
        max_lean_predecessors=args.max_lean_predecessors,
    )
    records = read_jsonl(args.input)
    validator = SpanValidator(args.project_root)
    selected, reason_counts, method_counts = select_records(records, config, validator, selected_at=started.isoformat())
    write_jsonl(args.output, selected)
    elapsed = (datetime.now(timezone.utc) - started).total_seconds()
    args.report_output.write_text(
        report_markdown(
            input_path=args.input,
            output_path=args.output,
            records=records,
            selected=selected,
            reason_counts=reason_counts,
            method_counts=method_counts,
            config=config,
            elapsed_seconds=elapsed,
        ),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "input_records": len(records),
                "selected_records": len(selected),
                "rejected_records": len(records) - len(selected),
                "output": args.output.as_posix(),
                "report": args.report_output.as_posix(),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
