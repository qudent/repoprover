#!/usr/bin/env python3
"""Summarize source-only prompt/context risks from a budget run."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _user_payload(path: Path) -> dict[str, Any]:
    payload = _read_json(path)
    for message in payload.get("messages", []):
        if message.get("role") != "user":
            continue
        content = message.get("content")
        if not isinstance(content, str):
            continue
        parsed = json.loads(content)
        if isinstance(parsed, dict):
            return parsed
    raise ValueError(f"no user JSON payload in {path}")


def audit_run(source_only_run: Path, context_comparison: Path) -> dict[str, Any]:
    comparison = _read_json(context_comparison)
    rows: list[dict[str, Any]] = []
    for row in comparison.get("results", []):
        index = int(row["index"])
        payload = _user_payload(source_only_run / f"record-{index:03d}" / "openrouter-payload.json")
        context = payload.get("context") or {}
        focus_rows = context.get("tex_source_focus") or []
        risks = sorted({str(risk) for focus in focus_rows for risk in focus.get("span_risks", [])})
        focused_envs = sum(len(focus.get("labeled_environment_focus", [])) for focus in focus_rows)
        removed_blocks = int(
            ((context.get("benchmark_policy") or {}).get("source_only_removed_hidden_target_context_blocks") or 0)
        )
        flags: list[str] = []
        if "broad_source_span" in risks:
            flags.append("broad")
        if "source_span_contains_multiple_theorem_environments" in risks:
            flags.append("multi-env")
        if "source_span_contains_extra_labels" in risks:
            flags.append("extra-labels")
        if "source_span_contains_multiple_parts" in risks:
            flags.append("multi-part")
        if row.get("target_comment_terms_absent_from_source"):
            flags.append("target-comment-gap")
        if focused_envs:
            flags.append("focused-label-env")
        if removed_blocks:
            flags.append("hidden-name-block-filtered")
        rows.append(
            {
                "index": index,
                "record_id": row.get("record_id"),
                "risks": risks,
                "flags": flags,
                "focused_labeled_environments": focused_envs,
                "removed_hidden_target_context_blocks": removed_blocks,
                "target_comment_terms_absent_from_source": row.get("target_comment_terms_absent_from_source") or [],
                "hidden_target_names_found_in_source_payload": row.get("hidden_target_names_found_in_source_payload") or [],
                "source_only_estimated_max_cost_usd": row.get("source_only_estimated_max_cost_usd"),
            }
        )
    summary = {
        "source_only_run": str(source_only_run),
        "context_comparison": str(context_comparison),
        "records": len(rows),
        "source_only_estimated_max_cost_usd": comparison.get("source_only_estimated_max_cost_usd"),
        "rows_with_hidden_target_names_in_source_payload": sum(
            1 for row in rows if row["hidden_target_names_found_in_source_payload"]
        ),
        "rows_with_target_comment_terms_absent_from_source": sum(
            1 for row in rows if row["target_comment_terms_absent_from_source"]
        ),
        "rows_with_broad_source_span": sum(1 for row in rows if "broad_source_span" in row["risks"]),
        "rows_with_multiple_theorem_environments": sum(
            1 for row in rows if "source_span_contains_multiple_theorem_environments" in row["risks"]
        ),
        "rows_with_extra_declared_labels": sum(
            1 for row in rows if "source_span_contains_extra_labels" in row["risks"]
        ),
        "rows_with_multiple_parts": sum(1 for row in rows if "source_span_contains_multiple_parts" in row["risks"]),
        "rows_with_focused_labeled_environment": sum(1 for row in rows if row["focused_labeled_environments"]),
        "focused_labeled_environments": sum(row["focused_labeled_environments"] for row in rows),
        "rows_with_hidden_target_context_blocks_removed": sum(
            1 for row in rows if row["removed_hidden_target_context_blocks"]
        ),
        "hidden_target_context_blocks_removed": sum(row["removed_hidden_target_context_blocks"] for row in rows),
        "results": rows,
    }
    return summary


def render_markdown(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# Source-Only Context Budget Audit",
        "",
        f"- Source-only run: `{summary['source_only_run']}`",
        f"- Context comparison: `{summary['context_comparison']}`",
        f"- Records: `{summary['records']}`",
        f"- Estimated max generation cost: `${float(summary['source_only_estimated_max_cost_usd'] or 0.0):.9f}`",
        f"- Hidden target-name rows: `{summary['rows_with_hidden_target_names_in_source_payload']}`",
        f"- Target-comment gap rows: `{summary['rows_with_target_comment_terms_absent_from_source']}`",
        f"- Broad source-span rows: `{summary['rows_with_broad_source_span']}`",
        f"- Multi-environment rows: `{summary['rows_with_multiple_theorem_environments']}`",
        f"- Extra-label rows: `{summary['rows_with_extra_declared_labels']}`",
        f"- Multi-part rows: `{summary['rows_with_multiple_parts']}`",
        f"- Rows with focused labeled environments: `{summary['rows_with_focused_labeled_environment']}`",
        f"- Focused labeled environments extracted: `{summary['focused_labeled_environments']}`",
        f"- Rows with hidden-name context blocks removed: `{summary['rows_with_hidden_target_context_blocks_removed']}`",
        f"- Hidden-name context blocks removed: `{summary['hidden_target_context_blocks_removed']}`",
        "",
        "## Highest-Risk Rows",
        "",
        "| # | Record | Flags | Missing Target-Comment Terms |",
        "|---:|---|---|---|",
    ]
    high_risk_rows = [
        row
        for row in summary["results"]
        if len([flag for flag in row["flags"] if flag != "focused-label-env"]) >= 3
    ]
    for row in high_risk_rows[:40]:
        lines.append(
            "| {index} | `{record}` | `{flags}` | `{terms}` |".format(
                index=row["index"],
                record=row["record_id"],
                flags=", ".join(row["flags"]),
                terms=", ".join(row["target_comment_terms_absent_from_source"][:8]),
            )
        )
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-only-run", type=Path, required=True)
    parser.add_argument("--context-comparison", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = audit_run(args.source_only_run, args.context_comparison)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    render_markdown(args.output_md, summary)
    print(json.dumps({key: value for key, value in summary.items() if key != "results"}, indent=2))


if __name__ == "__main__":
    main()
