#!/usr/bin/env python3
"""Review minimal-context pilot records with an OpenRouter model.

The script builds an evidence bundle from the published Algebraic
Combinatorics repository, asks a reviewer model to attack each record, and
writes both JSONL results and a compact Markdown summary. It is intentionally
separate from the main RepoProver coordinator so gold-standard work can be run
and costed without launching formalization agents.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from json import JSONDecodeError
from pathlib import Path
from typing import Any

from openai import OpenAI


DEFAULT_MODEL = "qwen/qwen3.6-35b-a3b"
DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_SOURCE_BASE = "https://raw.githubusercontent.com/facebookresearch/algebraic-combinatorics/main"


@dataclass(frozen=True)
class ReviewUsage:
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float | None


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


def fetch_text(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "repoprover-minimal-context-reviewer"})
    with urllib.request.urlopen(request, timeout=45) as response:
        return response.read().decode("utf-8")


def fetch_repo_file(path: str, source_base_url: str, cache_dir: Path | None) -> str:
    if path.startswith("http://") or path.startswith("https://"):
        url = path
        cache_key = re.sub(r"[^A-Za-z0-9_.-]+", "_", path)
    else:
        url = f"{source_base_url.rstrip('/')}/{path}"
        cache_key = path.replace("/", "__")

    if cache_dir is not None:
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_path = cache_dir / cache_key
        if cache_path.exists():
            return cache_path.read_text(encoding="utf-8")

    text = fetch_text(url)
    if cache_dir is not None:
        cache_path.write_text(text, encoding="utf-8")
    return text


def numbered_snippet(text: str, start: int, end: int, context: int = 0) -> str:
    lines = text.splitlines()
    if not lines:
        return ""
    lo = max(1, start - context)
    hi = min(len(lines), end + context)
    width = len(str(hi))
    return "\n".join(f"{line_no:>{width}}: {lines[line_no - 1]}" for line_no in range(lo, hi + 1))


def extract_declaration_hits(lean_text: str, names: list[str], max_line: int | None = None) -> list[dict[str, Any]]:
    lines = lean_text.splitlines()
    hits: list[dict[str, Any]] = []
    for full_name in names:
        short_name = full_name.split(".")[-1]
        pattern = re.compile(rf"^\s*(?:noncomputable\s+)?(?:theorem|lemma|def|abbrev|example)\s+{re.escape(short_name)}\b")
        for index, line in enumerate(lines, start=1):
            if pattern.search(line):
                snippet_end = min(index + 8, len(lines))
                if max_line is not None:
                    snippet_end = min(snippet_end, max_line)
                snippet = numbered_snippet(lean_text, index, snippet_end, context=0)
                hits.append({"declaration": full_name, "line": index, "snippet": snippet})
                break
        else:
            hits.append({"declaration": full_name, "line": None, "snippet": ""})
    return hits


def build_evidence_bundle(
    record: dict[str, Any],
    source_base_url: str,
    cache_dir: Path | None,
    source_context: int,
    lean_context: int,
) -> dict[str, Any]:
    output = record["output"]
    minimal_context = record["minimal_context"]
    lean_path = output["lean_path"]
    lean_text = fetch_repo_file(lean_path, source_base_url, cache_dir)
    lean_start, lean_end = output["line_range"]

    source_snippets = []
    for span in minimal_context.get("source_spans", []):
        source_text = fetch_repo_file(span["path"], source_base_url, cache_dir)
        start, end = span["line_range"]
        source_snippets.append(
            {
                "path": span["path"],
                "line_range": [start, end],
                "labels": span.get("labels", []),
                "snippet": numbered_snippet(source_text, start, end, context=source_context),
            }
        )

    return {
        "record": record,
        "lean_output": {
            "path": lean_path,
            "line_range": [lean_start, lean_end],
            "snippet": numbered_snippet(lean_text, lean_start, lean_end, context=lean_context),
            "declaration_hits": extract_declaration_hits(
                lean_text,
                output.get("declaration_names", []),
                max_line=lean_end,
            ),
        },
        "source_spans": source_snippets,
    }


def extract_json_object(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if not stripped:
        raise ValueError("reviewer returned an empty response")
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", stripped, flags=re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


def openrouter_prices(model_ids: list[str]) -> dict[str, tuple[float, float]]:
    try:
        data = json.loads(fetch_text("https://openrouter.ai/api/v1/models"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return {}
    by_id = {entry.get("id"): entry for entry in data.get("data", [])}
    prices: dict[str, tuple[float, float]] = {}
    for model_id in model_ids:
        entry = by_id.get(model_id)
        if not entry:
            continue
        pricing = entry.get("pricing", {})
        prices[model_id] = (float(pricing.get("prompt", 0.0)), float(pricing.get("completion", 0.0)))
    return prices


def estimate_usage(response: Any, model: str, prices: dict[str, tuple[float, float]]) -> ReviewUsage:
    usage = getattr(response, "usage", None)
    prompt_tokens = int(getattr(usage, "prompt_tokens", 0) or 0)
    completion_tokens = int(getattr(usage, "completion_tokens", 0) or 0)
    cost_usd = None
    if model in prices:
        input_price, output_price = prices[model]
        cost_usd = prompt_tokens * input_price + completion_tokens * output_price
    return ReviewUsage(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens, cost_usd=cost_usd)


def review_prompt(evidence: dict[str, Any]) -> list[dict[str, str]]:
    system = (
        "You are an adversarial Lean formalization benchmark reviewer. "
        "Your job is to decide whether a minimal-context record contains the smallest sufficient "
        "LaTeX and Lean context needed to reproduce the provided Lean output. "
        "Only declarations inside record.output.line_range are the target output; do not treat "
        "neighboring context lines as declarations that the record must justify. "
        "Prefer concrete missing-context and oversized-context findings over praise. "
        "Return exactly one JSON object and no markdown."
    )
    schema = {
        "record_id": "string",
        "verdict": "reject | revise | provisionally_accept",
        "source_span_assessment": "short string",
        "lean_context_assessment": "short string",
        "missing_context": ["specific missing source, import, predecessor, notation, or Mathlib facts"],
        "oversized_context": ["specific context that can be removed or narrowed"],
        "label_or_line_issues": ["specific label or line-range problems"],
        "recommended_record_edits": ["actionable edits to the JSONL record"],
        "trust_updates": {
            "source_span": "number from 0 to 1",
            "lean_dependency_graph": "number from 0 to 1",
            "model_extraction": "number from 0 to 1",
            "human_review": "number from 0 to 1",
        },
        "review_notes": ["durable notes to add to the record"],
    }
    user = (
        "Review this minimal-context record. Use only the provided evidence, and say when evidence is insufficient.\n\n"
        f"Required JSON schema:\n{json.dumps(schema, indent=2)}\n\n"
        f"Evidence:\n{json.dumps(evidence, indent=2)}"
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def call_reviewer(
    client: OpenAI,
    model: str,
    evidence: dict[str, Any],
    max_tokens: int,
    temperature: float,
    prices: dict[str, tuple[float, float]],
    extra_body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "model": model,
        "messages": review_prompt(evidence),
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if extra_body:
        kwargs["extra_body"] = extra_body
    response = client.chat.completions.create(**kwargs)
    content = response.choices[0].message.content or ""
    try:
        parsed = extract_json_object(content)
    except (JSONDecodeError, ValueError) as exc:
        parsed = {
            "record_id": evidence["record"]["id"],
            "verdict": "parse_error",
            "source_span_assessment": "",
            "lean_context_assessment": "",
            "missing_context": [],
            "oversized_context": [],
            "label_or_line_issues": [],
            "recommended_record_edits": ["Rerun this record; reviewer output was not parseable JSON."],
            "trust_updates": {
                "source_span": evidence["record"].get("trust", {}).get("source_span", 0),
                "lean_dependency_graph": evidence["record"].get("trust", {}).get("lean_dependency_graph", 0),
                "model_extraction": evidence["record"].get("trust", {}).get("model_extraction", 0),
                "human_review": 0,
            },
            "review_notes": [f"Reviewer response parse failed: {exc}"],
        }
    usage = estimate_usage(response, model, prices)
    return {
        "review": parsed,
        "raw_response": content,
        "usage": {
            "prompt_tokens": usage.prompt_tokens,
            "completion_tokens": usage.completion_tokens,
            "cost_usd": usage.cost_usd,
        },
    }


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def write_summary(path: Path, rows: list[dict[str, Any]], records_path: Path) -> None:
    total_prompt = sum(row["usage"].get("prompt_tokens") or 0 for row in rows)
    total_completion = sum(row["usage"].get("completion_tokens") or 0 for row in rows)
    costs = [row["usage"].get("cost_usd") for row in rows]
    total_cost = sum(cost for cost in costs if isinstance(cost, int | float))

    lines = [
        "# Minimal-Context Pilot Review",
        "",
        f"Records reviewed: {len(rows)} from `{records_path}`.",
        f"Reviewer model: `{rows[0]['model']}`." if rows else "Reviewer model: n/a.",
        f"Run timestamp: `{rows[0]['reviewed_at']}`." if rows else "Run timestamp: n/a.",
        f"Token usage: {total_prompt:,} prompt / {total_completion:,} completion.",
    ]
    if any(cost is not None for cost in costs):
        lines.append(f"Estimated OpenRouter cost: `${total_cost:.6f}`.")
    lines.extend(["", "## Findings", ""])

    for row in rows:
        review = row["review"]
        usage = row["usage"]
        cost = usage.get("cost_usd")
        cost_text = f", ${cost:.6f}" if isinstance(cost, int | float) else ""
        lines.extend(
            [
                f"### {review.get('record_id', row['record_id'])}",
                "",
                f"- Verdict: `{review.get('verdict', 'unknown')}` "
                f"({usage.get('prompt_tokens', 0):,} prompt / {usage.get('completion_tokens', 0):,} completion{cost_text}).",
                f"- Source span: {review.get('source_span_assessment', '')}",
                f"- Lean context: {review.get('lean_context_assessment', '')}",
            ]
        )
        for field, title in [
            ("missing_context", "Missing context"),
            ("oversized_context", "Oversized context"),
            ("label_or_line_issues", "Line or label issues"),
            ("recommended_record_edits", "Recommended edits"),
            ("review_notes", "Review notes"),
        ]:
            values = review.get(field) or []
            if not values:
                continue
            lines.append(f"- {title}:")
            for value in values:
                lines.append(f"  - {value}")
        if review.get("trust_updates"):
            lines.append(f"- Trust updates: `{json.dumps(review['trust_updates'], sort_keys=True)}`")
        lines.append("")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--records",
        type=Path,
        default=Path("docs/minimal-context-pilot-records.jsonl"),
        help="Input minimal-context JSONL records.",
    )
    parser.add_argument("--model", default=DEFAULT_MODEL, help="OpenRouter reviewer model.")
    parser.add_argument("--output", type=Path, default=Path("docs/minimal-context-review.jsonl"))
    parser.add_argument("--summary", type=Path, default=Path("docs/minimal-context-review-report.md"))
    parser.add_argument("--source-base-url", default=DEFAULT_SOURCE_BASE)
    parser.add_argument("--cache-dir", type=Path, default=Path(".cache/minimal-context-sources"))
    parser.add_argument("--limit", type=int, default=0, help="Limit number of records reviewed.")
    parser.add_argument("--max-tokens", type=int, default=4096)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument(
        "--reasoning-effort",
        choices=["none", "minimal", "low", "medium", "high", "xhigh"],
        help="OpenRouter reasoning effort override; use 'none' for schema-bound JSON review.",
    )
    parser.add_argument("--source-context", type=int, default=6)
    parser.add_argument("--lean-context", type=int, default=0)
    parser.add_argument("--dry-run", action="store_true", help="Build evidence only; do not call OpenRouter.")
    args = parser.parse_args()

    records = read_jsonl(args.records)
    if args.limit:
        records = records[: args.limit]
    if not records:
        print("error: no records selected", file=sys.stderr)
        return 1

    evidence_bundles = [
        build_evidence_bundle(
            record,
            source_base_url=args.source_base_url,
            cache_dir=args.cache_dir,
            source_context=args.source_context,
            lean_context=args.lean_context,
        )
        for record in records
    ]

    if args.dry_run:
        print(json.dumps(evidence_bundles, indent=2))
        return 0

    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print("error: OPENROUTER_API_KEY is not set", file=sys.stderr)
        return 1

    client = OpenAI(base_url=DEFAULT_BASE_URL, api_key=api_key)
    prices = openrouter_prices([args.model])
    extra_body = (
        {"reasoning": {"effort": args.reasoning_effort, "exclude": True}}
        if args.reasoning_effort
        else None
    )
    reviewed_at = datetime.now(timezone.utc).isoformat()

    rows: list[dict[str, Any]] = []
    for evidence in evidence_bundles:
        record = evidence["record"]
        result = call_reviewer(
            client=client,
            model=args.model,
            evidence=evidence,
            max_tokens=args.max_tokens,
            temperature=args.temperature,
            prices=prices,
            extra_body=extra_body,
        )
        rows.append(
            {
                "record_id": record["id"],
                "reviewed_at": reviewed_at,
                "model": args.model,
                "evidence_summary": {
                    "lean_path": record["output"]["lean_path"],
                    "lean_line_range": record["output"]["line_range"],
                    "source_spans": [
                        {
                            "path": span["path"],
                            "line_range": span["line_range"],
                            "labels": span.get("labels", []),
                        }
                        for span in record["minimal_context"].get("source_spans", [])
                    ],
                },
                **result,
            }
        )
        write_jsonl(args.output, rows)
        write_summary(args.summary, rows, args.records)
        usage = result["usage"]
        cost = usage.get("cost_usd")
        cost_text = f", ${cost:.6f}" if isinstance(cost, int | float) else ""
        print(
            f"reviewed {record['id']}: {usage.get('prompt_tokens', 0)} prompt / "
            f"{usage.get('completion_tokens', 0)} completion{cost_text}",
            file=sys.stderr,
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
