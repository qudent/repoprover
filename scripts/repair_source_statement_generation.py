#!/usr/bin/env python3
"""Generate repair attempts for archived source-statement generation failures."""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import threading
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.materialize_minimal_context_smoke import load_jsonl  # noqa: E402
from scripts.run_minimal_context_eval import DEFAULT_MODEL, write_json  # noqa: E402
from scripts.review_minimal_context_records import DEFAULT_BASE_URL  # noqa: E402
from scripts.run_source_statement_live_eval import (  # noqa: E402
    build_payload,
    build_repair_messages,
    call_openrouter,
    estimate_payload_cost,
    parse_model_json,
    response_finish_reason,
    response_message_content,
    summarize_openrouter_response_cost,
    write_jsonl,
    write_repair_model_artifacts,
)


def load_shape_warning_rows(run_output: Path, results_name: str | None) -> dict[int, list[dict[str, Any]]]:
    if not results_name:
        return {}
    path = run_output / "eval" / results_name
    if not path.exists():
        raise FileNotFoundError(f"shape diagnostic results not found: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows: dict[int, list[dict[str, Any]]] = {}
    for row in payload.get("results", []):
        warnings = row.get("warnings") or []
        if warnings:
            rows[int(row["index"])] = list(warnings)
    return rows


def load_repair_tasks(args: argparse.Namespace) -> list[dict[str, Any]]:
    selected_rows = load_jsonl(args.run_output / "eval" / "selected-records.jsonl")
    verification = json.loads((args.run_output / "eval" / args.verification_results).read_text(encoding="utf-8"))
    shape_warnings_by_index = load_shape_warning_rows(args.run_output, args.shape_diagnostic_results)
    selected_indices = set(args.indices or [])
    tasks: list[dict[str, Any]] = []
    for row in verification.get("results", []):
        index = int(row["index"])
        if selected_indices and index not in selected_indices:
            continue
        shape_warnings = shape_warnings_by_index.get(index, [])
        compile_failure = row.get("failure_class") == "generated_lean_does_not_compile"
        selected_by_failure = False if args.shape_warnings_only else compile_failure or args.include_non_compile_failures
        selected_by_shape = args.include_shape_warnings and bool(shape_warnings)
        if not selected_by_failure and not selected_by_shape:
            continue
        record_dir = args.run_output / f"record-{index:03d}"
        failed_model_path = record_dir / args.failed_model_output_name
        lean_result_path = record_dir / args.generated_only_lean_name
        payload_path = record_dir / "openrouter-payload.json"
        if index < 1 or index > len(selected_rows):
            continue
        if not failed_model_path.exists() or not lean_result_path.exists() or not payload_path.exists():
            tasks.append(
                {
                    "index": index,
                    "record_id": row.get("record_id"),
                    "record_dir": str(record_dir),
                    "success": False,
                    "failure_class": "missing_repair_input",
                    "error": f"missing one of {failed_model_path}, {lean_result_path}, {payload_path}",
                }
            )
            continue
        failed_model = json.loads(failed_model_path.read_text(encoding="utf-8"))
        lean_result = json.loads(lean_result_path.read_text(encoding="utf-8"))
        original_payload = json.loads(payload_path.read_text(encoding="utf-8"))
        messages = build_repair_messages(
            original_messages=original_payload["messages"],
            failed_declaration=str(failed_model.get("lean_declaration") or ""),
            generated_only_lean_result=lean_result,
            shape_diagnostic_warnings=shape_warnings,
        )
        repair_payload = build_payload(
            model=args.model,
            messages=messages,
            max_tokens=args.max_tokens,
            temperature=args.temperature,
            reasoning_effort=args.reasoning_effort,
        )
        tasks.append(
            {
                "index": index,
                "record_id": row.get("record_id"),
                "record_dir": str(record_dir),
                "payload": repair_payload,
                "budget_estimate": estimate_payload_cost(repair_payload),
                "shape_warning_codes": [warning.get("code") for warning in shape_warnings],
            }
        )
    return tasks


def repair_task(args: argparse.Namespace, task: dict[str, Any], cost_state: dict[str, float], lock: threading.Lock) -> dict[str, Any]:
    if "payload" not in task:
        return task
    record_dir = Path(task["record_dir"])
    prefix = f"repair-attempt-{args.attempt:03d}"
    write_json(record_dir / f"{prefix}-openrouter-payload.json", task["payload"])

    row: dict[str, Any] = {
        "index": task["index"],
        "record_id": task["record_id"],
        "record_dir": str(record_dir),
        "attempt": args.attempt,
        "budget_estimate": task["budget_estimate"],
        "shape_warning_codes": task.get("shape_warning_codes", []),
    }
    if args.budget_only:
        row["status"] = "budget_only"
        row["success"] = False
        row["paid_call_made"] = False
        return row

    with lock:
        if cost_state["actual_cost_usd"] >= args.max_actual_cost_usd:
            row["success"] = False
            row["paid_call_made"] = False
            row["failure_class"] = "cost_cap_reached"
            row["error"] = "global cost cap already reached; no request launched"
            return row

    try:
        response = call_openrouter(task["payload"], args.base_url, args.openrouter_timeout)
    except Exception as exc:  # noqa: BLE001
        row["api_request_attempted"] = True
        row["response_received"] = False
        row["success"] = False
        row["failure_class"] = f"openrouter_{type(exc).__name__}"
        row["error"] = str(exc)
        return row

    row["api_request_attempted"] = True
    row["response_received"] = True
    write_json(record_dir / f"{prefix}-openrouter-response.json", response)
    cost_summary = summarize_openrouter_response_cost(response)
    write_json(record_dir / f"{prefix}-openrouter-cost-summary.json", cost_summary)
    row["cost_summary"] = cost_summary
    row["finish_reason"] = response_finish_reason(response)
    actual_cost = cost_summary.get("actual_cost_usd")
    if actual_cost is not None:
        with lock:
            cost_state["actual_cost_usd"] += float(actual_cost)

    assistant_content = response_message_content(response)
    try:
        if not assistant_content.strip():
            raise ValueError("model returned empty content")
        model_json = parse_model_json(response)
        write_repair_model_artifacts(record_dir, args.attempt, assistant_content=assistant_content, model_json=model_json)
        row["success"] = True
        row["repair_generation_success"] = True
        row["generated_name"] = str(model_json.get("declaration_name") or "")
    except Exception as exc:  # noqa: BLE001
        row["success"] = False
        row["failure_class"] = f"model_json_{type(exc).__name__}"
        row["error"] = str(exc)
    return row


def aggregate_failure_classes(results: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in results:
        failure_class = row.get("failure_class")
        if failure_class:
            counts[str(failure_class)] = counts.get(str(failure_class), 0) + 1
    return dict(sorted(counts.items()))


def render_markdown(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# Source-statement generation repair",
        "",
        f"- Generated at: `{summary['generated_at']}`",
        f"- Run output: `{summary['run_output']}`",
        f"- Attempt: `{summary['attempt']}`",
        f"- Records: {summary['records_completed']}",
        f"- Repair generations: {summary['repair_generation_successes']}",
        f"- Paid calls: {summary['paid_calls_made']}",
        f"- Actual cost USD: `{summary['actual_cost_usd']}`",
        f"- Failure classes: `{json.dumps(summary['failure_classes'], sort_keys=True)}`",
        "",
        "| # | Result | Record | Generated name | Failure |",
        "|---:|---|---|---|---|",
    ]
    for row in summary["results"]:
        result = "BUDGET" if row.get("status") == "budget_only" else "PASS" if row.get("repair_generation_success") else "FAIL"
        lines.append(
            f"| {row['index']} | {result} | `{row.get('record_id') or ''}` | `{row.get('generated_name') or ''}` | `{row.get('failure_class') or ''}` |"
        )
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def run(args: argparse.Namespace) -> dict[str, Any]:
    tasks = load_repair_tasks(args)
    cost_state = {"actual_cost_usd": 0.0}
    lock = threading.Lock()
    results_by_index: dict[int, dict[str, Any]] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        futures = [executor.submit(repair_task, args, task, cost_state, lock) for task in tasks]
        for future in concurrent.futures.as_completed(futures):
            row = future.result()
            results_by_index[int(row["index"])] = row

    results = [results_by_index[index] for index in sorted(results_by_index)]
    repair_successes = [row for row in results if row.get("repair_generation_success")]
    paid_calls = sum(1 for row in results if row.get("response_received"))
    actual_cost = 0.0
    for row in results:
        cost = (row.get("cost_summary") or {}).get("actual_cost_usd")
        if cost is not None:
            actual_cost += float(cost)

    prefix = f"repair-attempt-{args.attempt:03d}"
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "run_output": str(args.run_output),
        "attempt": args.attempt,
        "records_completed": len(results),
        "repair_generation_successes": len(repair_successes),
        "repair_generation_success_rate": (len(repair_successes) / len(results)) if results else None,
        "paid_calls_made": paid_calls,
        "actual_cost_usd": actual_cost,
        "model": args.model,
        "max_tokens": args.max_tokens,
        "reasoning_effort": args.reasoning_effort,
        "concurrency": args.concurrency,
        "budget_only": args.budget_only,
        "shape_diagnostic_results": args.shape_diagnostic_results,
        "include_shape_warnings": args.include_shape_warnings,
        "shape_warnings_only": args.shape_warnings_only,
        "max_actual_cost_usd": args.max_actual_cost_usd,
        "failure_classes": aggregate_failure_classes(results),
        "results": results,
    }
    eval_dir = args.run_output / "eval"
    write_json(eval_dir / f"{prefix}-results.json", summary)
    write_jsonl(eval_dir / f"{prefix}-results.jsonl", results)
    render_markdown(eval_dir / f"{prefix}-results.md", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-output", type=Path, required=True)
    parser.add_argument("--verification-results", default="verification-results.json")
    parser.add_argument("--failed-model-output-name", default="model-output.json")
    parser.add_argument("--generated-only-lean-name", default="verification-generated-only-lean.json")
    parser.add_argument("--attempt", type=int, default=1)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--max-tokens", type=int, default=32768)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--reasoning-effort", default="high")
    parser.add_argument("--openrouter-timeout", type=float, default=240.0)
    parser.add_argument("--max-actual-cost-usd", type=float, default=0.25)
    parser.add_argument("--concurrency", type=int, default=3)
    parser.add_argument("--budget-only", action="store_true")
    parser.add_argument("--include-non-compile-failures", action="store_true")
    parser.add_argument(
        "--shape-diagnostic-results",
        default=None,
        help="Optional eval/ artifact with visible-context shape warnings to include in repair prompts.",
    )
    parser.add_argument(
        "--include-shape-warnings",
        action="store_true",
        help="Target rows that have shape diagnostic warnings, even when generated-only Lean compiled.",
    )
    parser.add_argument(
        "--shape-warnings-only",
        action="store_true",
        help="When using --include-shape-warnings, skip ordinary compile-failure selection and target only warning rows.",
    )
    parser.add_argument(
        "--indices",
        type=int,
        nargs="*",
        default=None,
        help="Optional 1-based record indices to target from the selected run.",
    )
    args = parser.parse_args()
    if args.concurrency < 1:
        raise ValueError("--concurrency must be at least 1")
    if args.attempt < 1:
        raise ValueError("--attempt must be at least 1")
    if args.shape_warnings_only and not args.include_shape_warnings:
        raise ValueError("--shape-warnings-only requires --include-shape-warnings")
    return args


if __name__ == "__main__":
    summary = run(parse_args())
    print(json.dumps({key: value for key, value in summary.items() if key != "results"}, indent=2))
