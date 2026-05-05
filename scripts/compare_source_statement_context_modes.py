#!/usr/bin/env python3
"""Compare target-comment and source-only source-statement prompt artifacts."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


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


def _domains(user_payload: dict[str, Any]) -> list[str]:
    context = user_payload.get("context") or {}
    guidance = context.get("domain_statement_shape_guidance") or []
    return [str(row.get("domain")) for row in guidance if row.get("domain")]


def _source_text(user_payload: dict[str, Any]) -> str:
    context = user_payload.get("context") or {}
    snippets = context.get("source_statement_or_chunk") or []
    return "\n".join(str(snippet.get("snippet") or "") for snippet in snippets)


def _target_comment_text(user_payload: dict[str, Any]) -> str:
    context = user_payload.get("context") or {}
    focus = context.get("target_source_focus") or {}
    comment = focus.get("target_declaration_source_comment") or {}
    return str(comment.get("text") or "")


def _context_mode(user_payload: dict[str, Any]) -> str:
    context = user_payload.get("context") or {}
    return str(context.get("context_mode") or "")


def _important_comment_terms(comment: str, source: str) -> list[str]:
    """Return target-comment words/phrases absent from source text.

    This is deliberately simple. The audit is a triage signal, not semantic
    proof that a source-only prompt is under-specified.
    """

    source_lower = source.lower()
    terms: list[str] = []
    for raw in re.findall(r"[A-Za-z][A-Za-z0-9_']{5,}", comment):
        term = raw.strip("`'").lower()
        if term in {"theorem", "lemma", "proposition", "definition", "target", "source", "label"}:
            continue
        if term not in source_lower and term not in terms:
            terms.append(term)
    return terms[:12]


def _lean_identifier_pattern(identifier: str) -> re.Pattern[str]:
    return re.compile(rf"(?<![A-Za-z0-9_'.]){re.escape(identifier)}(?![A-Za-z0-9_'])")


def _contains_any_identifier(text: str, needles: list[str]) -> list[str]:
    found: list[str] = []
    for needle in needles:
        if needle and _lean_identifier_pattern(needle).search(text):
            found.append(needle)
    return found


def compare_runs(target_comment_run: Path, source_only_run: Path) -> dict[str, Any]:
    selected_rows = _read_jsonl(source_only_run / "eval" / "selected-records.jsonl")
    source_summary = _read_json(source_only_run / "eval" / "source-statement-live-results.json")
    target_summary = _read_json(target_comment_run / "eval" / "source-statement-live-results.json")
    source_results_by_index = {int(row["index"]): row for row in source_summary.get("results", [])}
    rows: list[dict[str, Any]] = []
    for index, selected in enumerate(selected_rows, start=1):
        target_payload = _user_payload(target_comment_run / f"record-{index:03d}" / "openrouter-payload.json")
        source_payload = _user_payload(source_only_run / f"record-{index:03d}" / "openrouter-payload.json")
        target_domains = _domains(target_payload)
        source_domains = _domains(source_payload)
        target_comment = _target_comment_text(target_payload)
        source_text = _source_text(source_payload)
        declaration_names = [str(name).split(".")[-1] for name in selected.get("output", {}).get("declaration_names", [])]
        source_payload_text = json.dumps(source_payload, ensure_ascii=False)
        rows.append(
            {
                "index": index,
                "record_id": selected.get("id") or selected.get("record_id"),
                "target_context_mode": _context_mode(target_payload),
                "source_context_mode": _context_mode(source_payload),
                "target_comment_present": bool(target_comment),
                "source_target_comment_present": bool(_target_comment_text(source_payload)),
                "target_domains": target_domains,
                "source_domains": source_domains,
                "lost_domains": [domain for domain in target_domains if domain not in source_domains],
                "target_comment_terms_absent_from_source": _important_comment_terms(target_comment, source_text),
                "hidden_target_names_found_in_source_payload": _contains_any_identifier(
                    source_payload_text, declaration_names
                ),
                "source_only_estimated_max_cost_usd": (
                    source_results_by_index.get(index, {}).get("budget_estimate", {}).get("estimated_max_cost_usd")
                ),
            }
        )
    return {
        "target_comment_run": str(target_comment_run),
        "source_only_run": str(source_only_run),
        "records": len(rows),
        "records_with_lost_domains": sum(1 for row in rows if row["lost_domains"]),
        "records_with_target_comment_terms_absent_from_source": sum(
            1 for row in rows if row["target_comment_terms_absent_from_source"]
        ),
        "records_with_hidden_target_names_in_source_payload": sum(
            1 for row in rows if row["hidden_target_names_found_in_source_payload"]
        ),
        "source_only_estimated_max_cost_usd": sum(
            float(row["source_only_estimated_max_cost_usd"] or 0.0) for row in rows
        ),
        "results": rows,
    }


def render_markdown(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# Source-Statement Context Mode Comparison",
        "",
        f"- Target-comment run: `{summary['target_comment_run']}`",
        f"- Source-only run: `{summary['source_only_run']}`",
        f"- Records: {summary['records']}",
        f"- Rows with lost guidance domains: {summary['records_with_lost_domains']}",
        (
            "- Rows with target-comment terms absent from source span: "
            f"{summary['records_with_target_comment_terms_absent_from_source']}"
        ),
        f"- Rows with hidden target names in source-only payload: {summary['records_with_hidden_target_names_in_source_payload']}",
        f"- Source-only estimated max cost: `${summary['source_only_estimated_max_cost_usd']:.9f}`",
        "",
        "| # | Record | Lost Domains | Comment Terms Missing From Source | Hidden Names In Source Payload |",
        "|---:|---|---|---|---|",
    ]
    for row in summary["results"]:
        lines.append(
            "| {index} | `{record}` | `{lost}` | `{terms}` | `{hidden}` |".format(
                index=row["index"],
                record=row["record_id"],
                lost=", ".join(row["lost_domains"]),
                terms=", ".join(row["target_comment_terms_absent_from_source"]),
                hidden=", ".join(row["hidden_target_names_found_in_source_payload"]),
            )
        )
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-comment-run", type=Path, required=True)
    parser.add_argument("--source-only-run", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = compare_runs(args.target_comment_run, args.source_only_run)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    render_markdown(args.output_md, summary)
    print(json.dumps({key: value for key, value in summary.items() if key != "results"}, indent=2))


if __name__ == "__main__":
    main()
