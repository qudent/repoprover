#!/usr/bin/env python3
"""Verify source-statement generation artifacts with reusable Lean projects."""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import queue
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.materialize_minimal_context_smoke import SelectedRecord, load_jsonl  # noqa: E402
from scripts.run_minimal_context_eval import write_json  # noqa: E402
from scripts.run_source_statement_live_eval import (  # noqa: E402
    classify_lean_failure,
    contains_forbidden_placeholder,
    extract_generated_name,
    materialize_candidate_project,
    run_lean,
)


def load_tasks(run_output: Path) -> list[dict[str, Any]]:
    selected_path = run_output / "eval" / "selected-records.jsonl"
    rows = load_jsonl(selected_path)
    tasks: list[dict[str, Any]] = []
    for index, row in enumerate(rows, start=1):
        record_dir = run_output / f"record-{index:03d}"
        model_output_path = record_dir / "model-output.json"
        if not model_output_path.exists():
            tasks.append(
                {
                    "index": index,
                    "record_id": str(row.get("id") or row.get("record_id")),
                    "record_dir": str(record_dir),
                    "success": False,
                    "failure_class": "missing_model_output",
                    "error": f"missing {model_output_path}",
                }
            )
            continue
        tasks.append(
            {
                "index": index,
                "record": row,
                "record_id": str(row.get("id") or row.get("record_id")),
                "record_dir": str(record_dir),
                "model_output_path": str(model_output_path),
            }
        )
    return tasks


def verify_task(args: argparse.Namespace, task: dict[str, Any], project_pool: queue.Queue[Path]) -> dict[str, Any]:
    if "record" not in task:
        return task

    project_dir = project_pool.get()
    try:
        record = SelectedRecord(task["record"])
        record_dir = Path(task["record_dir"])
        model_json = json.loads(Path(task["model_output_path"]).read_text(encoding="utf-8"))
        declaration = str(model_json.get("lean_declaration") or "")
        generated_name = extract_generated_name(declaration, model_json.get("declaration_name"))
        row: dict[str, Any] = {
            "index": task["index"],
            "record_id": task["record_id"],
            "record_dir": str(record_dir),
            "generated_name": generated_name,
        }
        if not declaration.strip() or not generated_name:
            row["success"] = False
            row["failure_class"] = "missing_declaration"
            return row
        if contains_forbidden_placeholder(declaration):
            row["success"] = False
            row["failure_class"] = "forbidden_placeholder"
            return row

        try:
            generated_target = materialize_candidate_project(
                project_root=args.project_root,
                output_root=project_dir,
                record=record,
                lean_declaration=declaration,
                generated_name=str(generated_name),
                lake_cache_from=args.lake_cache_from,
                include_record_imports=args.include_record_imports,
                include_grader=False,
                clean_output=False,
            )
            generated_only = run_lean(project_dir, generated_target, args.lean_timeout)
            write_json(record_dir / "verification-generated-only-lean.json", generated_only)
            row["generated_only_lean_check"] = generated_only
            if generated_only["exit_code"] != 0:
                row["success"] = False
                row["failure_class"] = "generated_lean_does_not_compile"
                return row

            graded_target = materialize_candidate_project(
                project_root=args.project_root,
                output_root=project_dir,
                record=record,
                lean_declaration=declaration,
                generated_name=str(generated_name),
                lake_cache_from=args.lake_cache_from,
                include_record_imports=args.include_record_imports,
                include_grader=True,
                clean_output=False,
            )
            graded = run_lean(project_dir, graded_target, args.lean_timeout)
            write_json(record_dir / "verification-graded-lean.json", graded)
            row["lean_check"] = graded
            row["success"] = graded["exit_code"] == 0
            if not row["success"]:
                row["failure_class"] = classify_lean_failure(str(graded.get("output") or ""))
            return row
        except Exception as exc:  # noqa: BLE001
            row["success"] = False
            row["failure_class"] = "verification_error"
            row["error"] = f"{type(exc).__name__}: {exc}"
            return row
    finally:
        project_pool.put(project_dir)


def aggregate_failure_classes(results: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in results:
        failure_class = row.get("failure_class")
        if failure_class:
            counts[str(failure_class)] = counts.get(str(failure_class), 0) + 1
    return dict(sorted(counts.items()))


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def render_markdown(path: Path, summary: dict[str, Any]) -> None:
    rate = summary["success_rate"]
    lines = [
        "# Source-statement generation verification",
        "",
        f"- Generated at: `{summary['generated_at']}`",
        f"- Run output: `{summary['run_output']}`",
        f"- Work root: `{summary['work_root']}`",
        f"- Workers: `{summary['workers']}`",
        f"- Records: {summary['records_completed']}",
        f"- Successes: {summary['successes']}",
        f"- Success rate: {rate:.1%}" if rate is not None else "- Success rate: n/a",
        f"- Failure classes: `{json.dumps(summary['failure_classes'], sort_keys=True)}`",
        "",
        "| # | Result | Record | Generated name | Failure |",
        "|---:|---|---|---|---|",
    ]
    for row in summary["results"]:
        result = "PASS" if row.get("success") else "FAIL"
        lines.append(
            f"| {row['index']} | {result} | `{row['record_id']}` | `{row.get('generated_name') or ''}` | `{row.get('failure_class') or ''}` |"
        )
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def run(args: argparse.Namespace) -> dict[str, Any]:
    if args.workers < 1:
        raise ValueError("--workers must be at least 1")
    tasks = load_tasks(args.run_output)
    if args.work_root.exists():
        shutil.rmtree(args.work_root)
    args.work_root.mkdir(parents=True)
    project_pool: queue.Queue[Path] = queue.Queue()
    for worker_index in range(1, args.workers + 1):
        project_pool.put(args.work_root / f"project-{worker_index:03d}")

    results_by_index: dict[int, dict[str, Any]] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = [executor.submit(verify_task, args, task, project_pool) for task in tasks]
        for future in concurrent.futures.as_completed(futures):
            row = future.result()
            results_by_index[int(row["index"])] = row

    results = [results_by_index[index] for index in sorted(results_by_index)]
    successes = [row for row in results if row.get("success")]
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "run_output": str(args.run_output),
        "work_root": str(args.work_root),
        "workers": args.workers,
        "records_completed": len(results),
        "successes": len(successes),
        "success_rate": (len(successes) / len(results)) if results else None,
        "failure_classes": aggregate_failure_classes(results),
        "results": results,
    }
    eval_dir = args.run_output / "eval"
    write_json(eval_dir / "verification-results.json", summary)
    write_jsonl(eval_dir / "verification-results.jsonl", results)
    render_markdown(eval_dir / "verification-results.md", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-output", type=Path, required=True)
    parser.add_argument("--project-root", type=Path, default=REPO_ROOT / "algebraic-combinatorics")
    parser.add_argument("--work-root", type=Path, required=True)
    parser.add_argument("--lake-cache-from", type=Path, default=None)
    parser.add_argument("--include-record-imports", action="store_true")
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--lean-timeout", type=int, default=90)
    return parser.parse_args()


if __name__ == "__main__":
    summary = run(parse_args())
    print(json.dumps({key: value for key, value in summary.items() if key != "results"}, indent=2))
