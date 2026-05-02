#!/usr/bin/env python3
"""Run a target-statement-withheld source-to-Lean live evaluation.

This is stricter than oracle proof-fill: prompts include the selected TeX/source
chunk plus prefix Lean context, but not the target Lean statement/skeleton/name.
For theorem/lemma records, grading appends the gold statement in a private check
name and tries to prove it from the model-generated theorem. The gold statement
is used only by the grader, never in the prompt.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from openai import OpenAI

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.materialize_minimal_context_smoke import (  # noqa: E402
    DECL_RE,
    SelectedRecord,
    copy_lake_cache,
    copy_project_config,
    context_close_commands,
    load_jsonl,
    read_line_range,
    render_ordered_context_and_predecessors,
)
from scripts.run_minimal_context_eval import (  # noqa: E402
    DEFAULT_MODEL,
    DEFAULT_PRICE,
    estimate_payload_cost,
    summarize_openrouter_response_cost,
    write_json,
    write_jsonl,
)
from scripts.review_minimal_context_records import DEFAULT_BASE_URL  # noqa: E402

GENERATED_DECL_RE = re.compile(
    r"^\s*(?:(?:private|protected|noncomputable|unsafe|partial)\s+)*"
    r"(?:theorem|lemma)\s+(?P<name>[^\s:\{\(\[]+)",
    re.MULTILINE,
)


@dataclass(frozen=True)
class SourceEvalRecord:
    index: int
    selected: SelectedRecord


def select_source_statement_records(rows: list[dict[str, Any]], limit: int) -> list[SourceEvalRecord]:
    candidates = [
        row
        for row in rows
        if len(row.get("output", {}).get("declaration_names", [])) == 1
        and row.get("output", {}).get("chunk_kind") in {"theorem", "lemma"}
        and row.get("minimal_context", {}).get("source_spans")
    ]
    candidates.sort(
        key=lambda row: (
            str(row.get("output", {}).get("lean_path", "")),
            int(row.get("output", {}).get("line_range", [0, 0])[0]),
            str(row.get("id") or row.get("record_id")),
        )
    )
    if limit <= 0 or limit >= len(candidates):
        picked = candidates
    elif limit == 1:
        picked = [candidates[0]]
    else:
        # Evenly spread through corpus order rather than taking only the easiest first N.
        picked = [candidates[round(i * (len(candidates) - 1) / (limit - 1))] for i in range(limit)]
    return [SourceEvalRecord(index=i, selected=SelectedRecord(row)) for i, row in enumerate(picked, start=1)]


def source_snippets(project_root: Path, record: SelectedRecord) -> list[dict[str, Any]]:
    snippets: list[dict[str, Any]] = []
    for span in record.source_spans:
        start, end = [int(value) for value in span["line_range"]]
        snippets.append(
            {
                "path": span["path"],
                "line_range": [start, end],
                "labels": span.get("labels", []),
                "snippet": read_line_range(project_root / str(span["path"]), (start, end)),
            }
        )
    return snippets


def build_prompt_context(project_root: Path, record: SelectedRecord) -> dict[str, Any]:
    context_parts, _ = render_ordered_context_and_predecessors(project_root, record)
    return {
        "source_statement_or_chunk": source_snippets(project_root, record),
        "lean_prefix_context": "\n".join(context_parts).strip(),
        "mathlib_context": record.mathlib_context,
        "benchmark_policy": {
            "target_lean_statement_available_to_model": False,
            "target_declaration_name_available_to_model": False,
            "grading_uses_withheld_gold_statement": True,
        },
    }


def build_messages(project_root: Path, record: SelectedRecord) -> list[dict[str, str]]:
    system = (
        "You are a Lean 4 autoformalization agent working in a Mathlib-only project. "
        "You must formalize the provided TeX/math source chunk into one Lean theorem or lemma, "
        "including a proof, using only the Lean prefix context provided. The target Lean statement, "
        "target declaration name, and original proof are intentionally withheld. Return exactly one JSON object."
    )
    schema = {
        "lean_declaration": "one complete Lean theorem or lemma, including proof/body; do not include imports or markdown",
        "declaration_name": "the local name you gave that theorem/lemma",
        "used_context": ["short list of source/context facts used"],
        "notes": ["brief caveats, if any"],
    }
    user = {
        "task": "Formalize the source chunk as one Lean theorem/lemma and prove it.",
        "required_json_schema": schema,
        "instructions": [
            "Do not use sorry, admit, aesop? placeholders, or comments standing in for proof.",
            "Do not include import statements; the generated file already imports Mathlib.",
            "Do not assume access to the withheld target Lean statement or name.",
            "Prefer a short proof if the prefix context already contains the needed fact.",
        ],
        "context": build_prompt_context(project_root, record),
    }
    return [{"role": "system", "content": system}, {"role": "user", "content": json.dumps(user, indent=2, ensure_ascii=False)}]


def build_payload(*, model: str, messages: list[dict[str, str]], max_tokens: int, temperature: float, reasoning_effort: str | None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "response_format": {"type": "json_object"},
    }
    if reasoning_effort:
        payload["extra_body"] = {"reasoning": {"effort": reasoning_effort, "exclude": True}}
    return payload


def extract_generated_name(declaration: str, declared_name: str | None) -> str | None:
    if declared_name:
        return declared_name.strip().strip("`")
    match = GENERATED_DECL_RE.search(declaration)
    if match:
        return match.group("name")
    return None


def gold_check_declaration(project_root: Path, record: SelectedRecord, generated_name: str) -> str:
    original = read_line_range(project_root / record.lean_path, record.line_range)
    marker = original.find(":=")
    if marker == -1:
        raise ValueError(f"target declaration lacks ':=': {record.record_id}")
    head = original[:marker].rstrip()
    head = re.sub(
        r"(\b(?:theorem|lemma)\s+)([^\s:\{\(\[]+)",
        r"\1__repoprover_source_statement_check",
        head,
        count=1,
    )
    return head + f" := by\n  simpa using {generated_name}\n"


def contains_forbidden_placeholder(declaration: str) -> bool:
    return bool(re.search(r"\b(sorry|admit|by\s*omega\s*\?)\b", declaration))


def materialize_candidate_project(
    *,
    project_root: Path,
    output_root: Path,
    record: SelectedRecord,
    lean_declaration: str,
    generated_name: str,
    lake_cache_from: Path | None,
) -> Path:
    if output_root.exists():
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True)
    copy_project_config(project_root, output_root)
    if lake_cache_from is not None:
        copy_lake_cache(lake_cache_from, output_root)

    context_parts, context_closes = render_ordered_context_and_predecessors(project_root, record)
    imports = ["Mathlib"]
    parts: list[str] = [*(f"import {module}" for module in imports), ""]
    parts.append("/-! Source-statement eval target. The target Lean statement was withheld from the model. -/")
    parts.append("")
    parts.extend(context_parts)
    if context_parts:
        parts.append("")
    parts.append("-- Model-generated declaration starts here.")
    parts.append(lean_declaration.strip())
    parts.append("")
    parts.append("-- Grader-only check: original target statement, proved from the model theorem.")
    parts.append(gold_check_declaration(project_root, record, generated_name).rstrip())
    parts.append("")
    parts.extend(context_closes)

    target_path = output_root / record.lean_path
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text("\n".join(parts).rstrip() + "\n", encoding="utf-8")
    return target_path


def run_lean(project_root: Path, target_path: Path, timeout: int) -> dict[str, Any]:
    rel = target_path.relative_to(project_root)
    proc = subprocess.run(
        ["uv", "run", "lake", "env", "lean", str(rel)],
        cwd=project_root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
        check=False,
    )
    return {"exit_code": proc.returncode, "output": proc.stdout[-8000:]}


def call_openrouter(payload: dict[str, Any], base_url: str, timeout: float) -> dict[str, Any]:
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY is not set")
    client = OpenAI(base_url=base_url, api_key=key, timeout=timeout, max_retries=0)
    response = client.chat.completions.create(**payload)
    return response.model_dump(mode="json")


def parse_model_json(response: dict[str, Any]) -> dict[str, Any]:
    content = response["choices"][0]["message"].get("content") or ""
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", content, flags=re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


def run(args: argparse.Namespace) -> dict[str, Any]:
    rows = load_jsonl(args.records)
    records = select_source_statement_records(rows, args.limit)
    if not records:
        raise ValueError("no theorem/lemma source-statement records selected")

    eval_dir = args.output / "eval"
    eval_dir.mkdir(parents=True, exist_ok=True)
    selected_rows = [item.selected.row for item in records]
    write_jsonl(eval_dir / "selected-records.jsonl", selected_rows)

    results: list[dict[str, Any]] = []
    total_actual_cost = 0.0
    paid_calls = 0
    for item in records:
        record = item.selected
        record_dir = args.output / f"record-{item.index:03d}"
        payload = build_payload(
            model=args.model,
            messages=build_messages(args.project_root, record),
            max_tokens=args.max_tokens,
            temperature=args.temperature,
            reasoning_effort=args.reasoning_effort,
        )
        estimate = estimate_payload_cost(payload)
        row: dict[str, Any] = {
            "index": item.index,
            "record_id": record.record_id,
            "lean_path": record.lean_path,
            "gold_declaration_names": record.declaration_names,
            "gold_line_range": list(record.line_range),
            "prompt_policy": "target Lean statement/name withheld; target source chunk provided",
            "budget_estimate": estimate,
        }
        write_json(record_dir / "openrouter-payload.json", payload)

        if args.budget_only:
            row["paid_call_made"] = False
            results.append(row)
            continue

        try:
            response = call_openrouter(payload, args.base_url, args.openrouter_timeout)
        except Exception as exc:  # noqa: BLE001 - timeout/API failure should not abort the batch.
            row["paid_call_made"] = True
            row["success"] = False
            row["error"] = f"openrouter_{type(exc).__name__}: {exc}"
            results.append(row)
            write_json(eval_dir / "partial-results.json", {"results": results})
            continue
        paid_calls += 1
        write_json(record_dir / "openrouter-response.json", response)
        cost_summary = summarize_openrouter_response_cost(response)
        write_json(record_dir / "openrouter-cost-summary.json", cost_summary)
        if cost_summary.get("actual_cost_usd") is not None:
            total_actual_cost += float(cost_summary["actual_cost_usd"])

        try:
            model_json = parse_model_json(response)
            declaration = str(model_json.get("lean_declaration") or "")
            generated_name = extract_generated_name(declaration, model_json.get("declaration_name"))
            row["model_json"] = model_json
            row["generated_name"] = generated_name
            row["forbidden_placeholder"] = contains_forbidden_placeholder(declaration)
            if not declaration.strip() or not generated_name:
                raise ValueError("missing lean_declaration or declaration_name")
            if row["forbidden_placeholder"]:
                raise ValueError("model output contains forbidden placeholder")
            target_path = materialize_candidate_project(
                project_root=args.project_root,
                output_root=record_dir / "project",
                record=record,
                lean_declaration=declaration,
                generated_name=generated_name,
                lake_cache_from=args.lake_cache_from,
            )
            lean_result = run_lean(record_dir / "project", target_path, args.lean_timeout)
            row["lean_check"] = lean_result
            row["success"] = lean_result["exit_code"] == 0
        except Exception as exc:  # noqa: BLE001 - per-record eval should continue.
            row["success"] = False
            row["error"] = f"{type(exc).__name__}: {exc}"
        row["paid_call_made"] = True
        row["cost_summary"] = cost_summary
        results.append(row)
        write_json(eval_dir / "partial-results.json", {"results": results})

        if args.max_actual_cost_usd and total_actual_cost >= args.max_actual_cost_usd:
            break

    attempted = [row for row in results if row.get("paid_call_made")]
    successes = [row for row in attempted if row.get("success")]
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "records_selected": len(records),
        "records_attempted": len(attempted),
        "successes": len(successes),
        "success_rate": (len(successes) / len(attempted)) if attempted else None,
        "paid_calls_made": paid_calls,
        "actual_cost_usd": total_actual_cost,
        "model": args.model,
        "max_tokens": args.max_tokens,
        "reasoning_effort": args.reasoning_effort,
        "results": results,
    }
    write_json(eval_dir / "source-statement-live-results.json", summary)
    render_markdown(eval_dir / "source-statement-live-results.md", summary)
    return summary


def render_markdown(path: Path, summary: dict[str, Any]) -> None:
    rate = summary["success_rate"]
    lines = [
        "# Source-statement live eval results",
        "",
        f"- Generated at: `{summary['generated_at']}`",
        f"- Model: `{summary['model']}`",
        f"- Max tokens: `{summary['max_tokens']}`",
        f"- Reasoning effort: `{summary['reasoning_effort']}`",
        f"- Records attempted: {summary['records_attempted']} / selected {summary['records_selected']}",
        f"- Successes: {summary['successes']}",
        f"- Success rate: {rate:.1%}" if rate is not None else "- Success rate: n/a",
        f"- Actual reported cost: `${summary['actual_cost_usd']:.6f}`",
        "",
        "Success means: the prompt withheld the target Lean statement/name; the model generated a theorem/lemma; the generated theorem compiled; and a grader-only copy of the gold statement was proved by `simpa using <generated theorem>`. This is still an oracle source-span benchmark, not full feed-forward segmentation.",
        "",
        "| # | Result | Record | Generated name | Cost | Error / Lean output |",
        "|---:|---|---|---|---:|---|",
    ]
    for row in summary["results"]:
        result = "✅" if row.get("success") else "❌"
        cost = row.get("cost_summary", {}).get("actual_cost_usd")
        cost_text = f"${float(cost):.6f}" if cost is not None else ""
        err = row.get("error") or row.get("lean_check", {}).get("output", "")
        err = " ".join(str(err).split())[:220]
        lines.append(
            f"| {row['index']} | {result} | `{row['record_id']}` | `{row.get('generated_name') or ''}` | {cost_text} | {err} |"
        )
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", type=Path, default=REPO_ROOT / "docs/minimal-context-splits/oracle_source_statement.jsonl")
    parser.add_argument("--project-root", type=Path, default=REPO_ROOT / "algebraic-combinatorics")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=30)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--max-tokens", type=int, default=32768)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--reasoning-effort", default="high")
    parser.add_argument("--lake-cache-from", type=Path, default=None)
    parser.add_argument("--lean-timeout", type=int, default=90)
    parser.add_argument("--openrouter-timeout", type=float, default=240.0)
    parser.add_argument("--max-actual-cost-usd", type=float, default=2.0)
    parser.add_argument("--budget-only", action="store_true")
    args = parser.parse_args()
    return args


if __name__ == "__main__":
    summary = run(parse_args())
    print(json.dumps({k: v for k, v in summary.items() if k != "results"}, indent=2))
