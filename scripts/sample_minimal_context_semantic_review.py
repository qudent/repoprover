#!/usr/bin/env python3
"""Select a deterministic semantic-review sample from gold candidates.

This is a local, zero-cost queue builder. It does not certify records; it
selects a small, diverse sample from mechanically accepted gold candidates so a
human or model reviewer can spend semantic-review budget on a reproducible set.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from scripts.filter_minimal_context_gold_candidates import read_jsonl, span_length, write_jsonl
except ModuleNotFoundError:
    from filter_minimal_context_gold_candidates import read_jsonl, span_length, write_jsonl


SAMPLE_SELECTOR_VERSION = "semantic-review-sample-v1"


def total_source_lines(record: dict[str, Any]) -> int:
    return sum(span_length(span["line_range"]) for span in record["minimal_context"].get("source_spans", []))


def output_lines(record: dict[str, Any]) -> int:
    return span_length(record["output"]["line_range"])


def predecessor_count(record: dict[str, Any]) -> int:
    return len(record["minimal_context"].get("lean_predecessors", []))


def difficulty_score(record: dict[str, Any]) -> int:
    return total_source_lines(record) + output_lines(record) + 4 * predecessor_count(record)


def difficulty_bin(score: int) -> str:
    if score <= 50:
        return "small"
    if score <= 95:
        return "medium"
    return "large"


def review_verdicts(rows: list[dict[str, Any]]) -> dict[str, str]:
    return {row["record_id"]: row["review"]["verdict"] for row in rows}


def stratum_for_record(record: dict[str, Any]) -> str:
    return f"{record['output'].get('chunk_kind', 'unknown')}:{difficulty_bin(difficulty_score(record))}"


def annotate_sample_record(record: dict[str, Any], *, stratum: str, selected_at: str, rank: int) -> dict[str, Any]:
    annotated = deepcopy(record)
    annotated["semantic_review_sample"] = {
        "selector_version": SAMPLE_SELECTOR_VERSION,
        "selected_at": selected_at,
        "rank": rank,
        "stratum": stratum,
        "metrics": {
            "source_lines": total_source_lines(record),
            "output_lines": output_lines(record),
            "lean_predecessors": predecessor_count(record),
            "difficulty_score": difficulty_score(record),
        },
        "caveat": "Queue sample only; not human- or model-certified semantic gold.",
    }
    return annotated


def select_sample(
    records: list[dict[str, Any]],
    static_verdicts: dict[str, str],
    *,
    limit: int,
    max_per_stratum: int,
    selected_at: str,
) -> list[dict[str, Any]]:
    eligible = [record for record in records if static_verdicts.get(record["id"]) == "provisionally_accept"]
    by_stratum: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in sorted(eligible, key=lambda row: (row.get("chapter_id") or "", row["id"])):
        by_stratum[stratum_for_record(record)].append(record)

    selected: list[dict[str, Any]] = []
    stratum_counts: Counter[str] = Counter()
    strata = sorted(by_stratum)
    while len(selected) < limit:
        progressed = False
        for stratum in strata:
            if len(selected) >= limit:
                break
            if stratum_counts[stratum] >= max_per_stratum:
                continue
            bucket = by_stratum[stratum]
            if not bucket:
                continue
            record = bucket.pop(0)
            stratum_counts[stratum] += 1
            selected.append(
                annotate_sample_record(record, stratum=stratum, selected_at=selected_at, rank=len(selected) + 1)
            )
            progressed = True
        if not progressed:
            break
    return selected


def report_markdown(
    *,
    records_path: Path,
    static_review_path: Path,
    output_path: Path,
    records: list[dict[str, Any]],
    static_verdicts: dict[str, str],
    selected: list[dict[str, Any]],
    limit: int,
    max_per_stratum: int,
) -> str:
    eligible_count = sum(1 for record in records if static_verdicts.get(record["id"]) == "provisionally_accept")
    selected_strata = Counter(row["semantic_review_sample"]["stratum"] for row in selected)
    selected_kinds = Counter(row["output"].get("chunk_kind", "unknown") for row in selected)
    selected_chapters = Counter((row.get("chapter_id") or "missing_chapter_id") for row in selected)
    payload = {
        "input_records": len(records),
        "mechanically_accepted_records": eligible_count,
        "selected_records": len(selected),
        "limit": limit,
        "max_per_stratum": max_per_stratum,
        "selected_kinds": dict(sorted(selected_kinds.items())),
        "selected_strata": dict(sorted(selected_strata.items())),
        "top_selected_chapters": selected_chapters.most_common(12),
        "model_cost_usd": 0.0,
    }

    lines = [
        "# Minimal Context Semantic Review Sample",
        "",
        "Generated by `scripts/sample_minimal_context_semantic_review.py`.",
        "",
        "## Hypothesis",
        "",
        "A small stratified sample should reveal semantic context-selection failures before spending review budget on all mechanically accepted candidates.",
        "",
        "## Artifacts",
        "",
        f"- Candidate input: `{records_path.as_posix()}`",
        f"- Static review input: `{static_review_path.as_posix()}`",
        f"- Sample JSONL: `{output_path.as_posix()}`",
        "- Model/API cost: `$0.00` (deterministic local sampling only)",
        "",
        "## Summary",
        "",
        "```json",
        json.dumps(payload, indent=2, sort_keys=True),
        "```",
        "",
        "## Trust Boundary",
        "",
        "Rows in this file are selected for semantic review; they are not certified semantic gold. Reviewers should still check source sufficiency, Lean predecessor necessity, and whether the output is reproducible from the mapped context.",
        "",
    ]
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", type=Path, default=Path("docs/minimal-context-gold-candidates.jsonl"))
    parser.add_argument(
        "--static-review",
        type=Path,
        default=Path("docs/minimal-context-gold-candidate-static-review.jsonl"),
    )
    parser.add_argument("--output", type=Path, default=Path("docs/minimal-context-semantic-review-sample.jsonl"))
    parser.add_argument("--report", type=Path, default=Path("docs/minimal-context-semantic-review-sample.md"))
    parser.add_argument("--limit", type=int, default=24)
    parser.add_argument("--max-per-stratum", type=int, default=3)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    selected_at = datetime.now(timezone.utc).isoformat()
    records = read_jsonl(args.records)
    static_rows = read_jsonl(args.static_review)
    static_verdicts = review_verdicts(static_rows)
    selected = select_sample(
        records,
        static_verdicts,
        limit=args.limit,
        max_per_stratum=args.max_per_stratum,
        selected_at=selected_at,
    )
    write_jsonl(args.output, selected)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        report_markdown(
            records_path=args.records,
            static_review_path=args.static_review,
            output_path=args.output,
            records=records,
            static_verdicts=static_verdicts,
            selected=selected,
            limit=args.limit,
            max_per_stratum=args.max_per_stratum,
        ),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "input_records": len(records),
                "selected_records": len(selected),
                "output": args.output.as_posix(),
                "report": args.report.as_posix(),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
