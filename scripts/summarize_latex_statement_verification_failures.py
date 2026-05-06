#!/usr/bin/env python3
"""Summarize theorem-level verification failures across one or more artifacts."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_json(path: Path, data: Any) -> None:
    write_text(path, json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n")


def message_signature(message: dict[str, Any]) -> str:
    data = str(message.get("data") or "").strip()
    if not data:
        return str(message.get("kind") or "empty_message")
    first_line = data.splitlines()[0].strip()
    return first_line[:180]


def unit_rows(summary: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for batch in summary.get("batches") or []:
        for unit in batch.get("units") or []:
            rows.append(unit)
    return rows


def summarize_one(path: Path) -> dict[str, Any]:
    summary = read_json(path)
    units = unit_rows(summary)
    failure_classes = Counter(str(unit.get("failure_class") or "unclassified") for unit in units)
    reported_statuses = Counter(str(unit.get("reported_status") or "unknown") for unit in units)
    contract_violations: Counter[str] = Counter()
    placeholder_tokens: Counter[str] = Counter()
    error_kinds: Counter[str] = Counter()
    error_signatures: Counter[str] = Counter()
    support_candidate_count = 0
    support_accepted_count = 0
    support_rejected_count = 0
    support_skipped_count = 0
    support_lean_call_count = 0
    support_elapsed_seconds = 0.0
    unit_summaries: list[dict[str, Any]] = []

    for unit in units:
        for violation in unit.get("contract_violations") or []:
            contract_violations[str(violation)] += 1
        for token in unit.get("placeholder_tokens") or []:
            placeholder_tokens[str(token)] += 1
        for message in unit.get("messages") or []:
            if message.get("severity") != "error":
                continue
            error_kinds[str(message.get("kind") or "unknown")] += 1
            error_signatures[message_signature(message)] += 1
        support = unit.get("visible_support_context") or {}
        support_candidate_count += int(support.get("candidate_count") or 0)
        support_accepted_count += int(support.get("accepted_count") or 0)
        support_rejected_count += int(support.get("rejected_count") or 0)
        support_skipped_count += int(support.get("skipped_count") or 0)
        support_lean_call_count += int(support.get("lean_call_count") or 0)
        support_elapsed_seconds += float(support.get("elapsed_seconds") or 0.0)
        unit_summaries.append(
            {
                "unit_key": unit.get("unit_key"),
                "failure_class": unit.get("failure_class"),
                "reported_status": unit.get("reported_status"),
                "compile_passed": unit.get("compile_passed"),
                "lean_error_count": unit.get("lean_error_count"),
                "lean_elapsed_seconds": unit.get("lean_elapsed_seconds"),
                "support": {
                    "candidate_count": support.get("candidate_count"),
                    "accepted_count": support.get("accepted_count"),
                    "rejected_count": support.get("rejected_count"),
                    "skipped_count": support.get("skipped_count"),
                    "lean_call_count": support.get("lean_call_count"),
                    "elapsed_seconds": support.get("elapsed_seconds"),
                },
            }
        )

    return {
        "verification_results": str(path),
        "generation_run": summary.get("generation_run"),
        "unit_count": len(units),
        "compile_passed_units": summary.get("compile_passed_units"),
        "failure_class_counts": dict(sorted(failure_classes.items())),
        "reported_status_counts": dict(sorted(reported_statuses.items())),
        "contract_violation_counts": dict(sorted(contract_violations.items())),
        "placeholder_token_counts": dict(sorted(placeholder_tokens.items())),
        "lean_error_kind_counts": dict(error_kinds.most_common(20)),
        "lean_error_signature_counts": dict(error_signatures.most_common(20)),
        "support_totals": {
            "candidate_count": support_candidate_count,
            "accepted_count": support_accepted_count,
            "rejected_count": support_rejected_count,
            "skipped_count": support_skipped_count,
            "lean_call_count": support_lean_call_count,
            "elapsed_seconds": round(support_elapsed_seconds, 3),
        },
        "lean_call_count": summary.get("lean_call_count"),
        "lean_elapsed_seconds": summary.get("lean_elapsed_seconds"),
        "units": unit_summaries,
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# LaTeX Statement Verification Failure Overview",
        "",
        f"Generated: `{report['generated_at']}`",
        "",
    ]
    for run in report["runs"]:
        lines.extend(
            [
                f"## `{run['generation_run']}`",
                "",
                f"- Verification: `{run['verification_results']}`",
                f"- Units: `{run['unit_count']}`; compiled: `{run['compile_passed_units']}`",
                f"- Failure classes: `{json.dumps(run['failure_class_counts'], sort_keys=True)}`",
                f"- Reported statuses: `{json.dumps(run['reported_status_counts'], sort_keys=True)}`",
                f"- Contract violations: `{json.dumps(run['contract_violation_counts'], sort_keys=True)}`",
                f"- Placeholder tokens: `{json.dumps(run['placeholder_token_counts'], sort_keys=True)}`",
                f"- Support totals: `{json.dumps(run['support_totals'], sort_keys=True)}`",
            ]
        )
        if run.get("lean_call_count") is not None:
            lines.append(
                f"- Lean calls/elapsed: `{run['lean_call_count']}` / `{run['lean_elapsed_seconds']}s`"
            )
        lines.extend(["", "Top Lean error signatures:"])
        if run["lean_error_signature_counts"]:
            for signature, count in run["lean_error_signature_counts"].items():
                escaped_signature = signature.replace("`", "\\`")
                lines.append(f"- `{count}` x {escaped_signature}")
        else:
            lines.append("- none")
        lines.extend(["", "Unit rows:"])
        for unit in run["units"]:
            support = unit["support"]
            lines.append(
                "- "
                f"`{unit['unit_key']}` {unit['failure_class']} status={unit['reported_status']} "
                f"errors={unit['lean_error_count']} "
                f"support={support.get('accepted_count')}/{support.get('candidate_count')} accepted"
            )
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verification-results", type=Path, action="append", required=True)
    parser.add_argument("--output-json", type=Path)
    parser.add_argument("--output-md", type=Path)
    args = parser.parse_args()

    report = {
        "schema_version": "repoprover.latex_statement_failure_overview.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "runs": [summarize_one(path) for path in args.verification_results],
    }
    if args.output_json:
        write_json(args.output_json, report)
    markdown = render_markdown(report)
    if args.output_md:
        write_text(args.output_md, markdown + "\n")
    print(markdown)


if __name__ == "__main__":
    main()
