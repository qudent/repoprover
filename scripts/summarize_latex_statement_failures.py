#!/usr/bin/env python3
"""Summarize theorem-level generation verification failure classes."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.verify_latex_statement_generation import failure_class_counts, verification_failure_class


DEFAULT_ROOTS = [
    Path("docs/latex-statement-generation-runs"),
    Path("docs/latex-statement-repair-loop-runs"),
]


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def count_values(values: list[str | None]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        key = value or "unknown"
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def verification_paths(roots: list[Path]) -> list[Path]:
    paths: list[Path] = []
    for root in roots:
        if root.is_file():
            paths.append(root)
            continue
        if root.exists():
            paths.extend(root.glob("**/eval/verification-results.json"))
    return sorted(dict.fromkeys(paths))


def iter_verification_units(data: dict[str, Any]) -> list[dict[str, Any]]:
    units: list[dict[str, Any]] = []
    for batch in data.get("batches") or []:
        for unit in batch.get("units") or []:
            normalized = dict(unit)
            normalized["failure_class"] = str(
                normalized.get("failure_class") or verification_failure_class(normalized)
            )
            units.append(normalized)
    return units


def selector_run_for_attempt(run_dir: Path) -> Path | None:
    for filename in ["generation-results.json", "repair-results.json"]:
        path = run_dir / "eval" / filename
        if not path.exists():
            continue
        data = read_json(path)
        selector_run = str(data.get("selector_run") or "")
        if selector_run:
            return Path(selector_run)
    return None


def source_ids_from_selector(selector_run: Path | None) -> dict[str, str]:
    if selector_run is None:
        return {}
    selected = read_jsonl(selector_run / "eval" / "selected-units.jsonl")
    return {
        f"unit-{index + 1:03d}": str(row.get("id") or "")
        for index, row in enumerate(selected)
        if row.get("id")
    }


def source_ids_from_gold(gold: dict[str, Any]) -> dict[str, str]:
    return {
        str(unit.get("unit_key") or ""): str(unit.get("source_unit_id") or "")
        for unit in gold.get("units") or []
        if unit.get("unit_key") and unit.get("source_unit_id")
    }


def first_error_text(unit: dict[str, Any]) -> str | None:
    for message in unit.get("messages") or []:
        if message.get("severity") == "error" and message.get("data"):
            return str(message["data"])[:400]
    stderr = str(unit.get("stderr") or "").strip()
    return stderr[:400] if stderr else None


def error_pattern(unit: dict[str, Any]) -> str | None:
    if unit.get("failure_class") == "compiled":
        return "compiled"
    violations = unit.get("contract_violations") or []
    if violations:
        return "contract_violation"
    text = first_error_text(unit) or ""
    if "failed to synthesize instance of type class" in text:
        return "missing_typeclass_or_binder"
    if text.startswith("Unknown constant"):
        return "unknown_constant"
    if text.startswith("Ambiguous term"):
        return "ambiguous_namespace_or_notation"
    if text.startswith("Application type mismatch"):
        return "application_type_mismatch"
    if text.startswith("unexpected token") or text.startswith("unexpected end of input"):
        return "syntax_error"
    if "unsolved goals" in text:
        return "incomplete_proof"
    if unit.get("skipped_reason") == "cannot_prove_from_visible_context":
        return "declined_cannot_prove"
    return "other"


def summarize_verification_path(path: Path, *, max_examples_per_class: int) -> dict[str, Any]:
    data = read_json(path)
    units = iter_verification_units(data)
    eval_dir = path.parent
    gold_path = eval_dir / "gold-comparison.json"
    gold = read_json(gold_path) if gold_path.exists() else {}
    run_dir = path.parent.parent
    source_ids = {
        **source_ids_from_selector(selector_run_for_attempt(run_dir)),
        **source_ids_from_gold(gold),
    }
    examples: dict[str, list[dict[str, Any]]] = {}
    source_units: list[dict[str, Any]] = []
    for unit in units:
        unit_key = str(unit.get("unit_key") or "")
        source_unit_id = source_ids.get(unit_key)
        source_units.append(
            {
                "source_unit_id": source_unit_id,
                "unit_key": unit_key,
                "failure_class": unit["failure_class"],
                "error_pattern": error_pattern(unit),
                "compile_passed": bool(unit.get("compile_passed")),
            }
        )
        failure_class = str(unit["failure_class"])
        bucket = examples.setdefault(failure_class, [])
        if len(bucket) >= max_examples_per_class:
            continue
        bucket.append(
            {
                "run": str(run_dir),
                "unit_key": unit_key,
                "source_unit_id": source_unit_id,
                "reported_status": unit.get("reported_status"),
                "error_pattern": error_pattern(unit),
                "contract_violations": unit.get("contract_violations") or [],
                "lean_returncode": unit.get("lean_returncode"),
                "lean_error_count": unit.get("lean_error_count"),
                "first_error": first_error_text(unit),
            }
        )
    return {
        "run": str(run_dir),
        "verification_results": str(path),
        "gold_comparison": str(gold_path) if gold_path.exists() else None,
        "unit_count": len(units),
        "compile_passed_units": sum(1 for unit in units if unit.get("compile_passed")),
        "failure_class_counts": failure_class_counts(units),
        "error_pattern_counts": count_values([error_pattern(unit) for unit in units]),
        "coverage_status_counts": gold.get("coverage_status_counts", {}),
        "source_units": source_units,
        "examples_by_class": examples,
    }


BEST_STATUS_RANK = {
    "compiled": 4,
    "declined_cannot_prove": 3,
    "compile_failure": 2,
    "contract_violation": 1,
}


def best_source_statuses(run_summaries: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    best: dict[str, dict[str, Any]] = {}
    for summary in run_summaries:
        for row in summary.get("source_units") or []:
            source_unit_id = row.get("source_unit_id")
            if not source_unit_id:
                continue
            failure_class = str(row.get("failure_class") or "unclassified")
            rank = BEST_STATUS_RANK.get(failure_class, 0)
            current = best.get(source_unit_id)
            if current is not None and BEST_STATUS_RANK.get(str(current.get("failure_class")), 0) >= rank:
                continue
            best[source_unit_id] = {
                "source_unit_id": source_unit_id,
                "failure_class": failure_class,
                "error_pattern": row.get("error_pattern"),
                "compile_passed": bool(row.get("compile_passed")),
                "best_run": summary.get("run"),
                "unit_key": row.get("unit_key"),
            }
    return dict(sorted(best.items()))


def merge_example_buckets(
    summaries: list[dict[str, Any]], *, max_examples_per_class: int
) -> dict[str, list[dict[str, Any]]]:
    merged: dict[str, list[dict[str, Any]]] = {}
    for summary in summaries:
        for failure_class, examples in (summary.get("examples_by_class") or {}).items():
            bucket = merged.setdefault(str(failure_class), [])
            for example in examples:
                if len(bucket) >= max_examples_per_class:
                    break
                bucket.append(example)
    return dict(sorted(merged.items()))


def summarize_roots(roots: list[Path], *, max_examples_per_class: int) -> dict[str, Any]:
    paths = verification_paths(roots)
    run_summaries = [
        summarize_verification_path(path, max_examples_per_class=max_examples_per_class)
        for path in paths
    ]
    all_units: list[dict[str, Any]] = []
    coverage_values: list[str | None] = []
    error_patterns: list[str | None] = []
    best_by_source = best_source_statuses(run_summaries)
    for summary in run_summaries:
        for failure_class, count in summary["failure_class_counts"].items():
            all_units.extend({"failure_class": failure_class} for _ in range(count))
        for pattern, count in summary["error_pattern_counts"].items():
            error_patterns.extend(str(pattern) for _ in range(count))
        for coverage_status, count in (summary.get("coverage_status_counts") or {}).items():
            coverage_values.extend(str(coverage_status) for _ in range(count))
    return {
        "schema_version": "repoprover.latex_statement_failure_taxonomy_summary.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "roots": [str(root) for root in roots],
        "verification_result_count": len(paths),
        "unit_count": sum(summary["unit_count"] for summary in run_summaries),
        "compile_passed_units": sum(summary["compile_passed_units"] for summary in run_summaries),
        "failure_class_counts": failure_class_counts(all_units),
        "error_pattern_counts": count_values(error_patterns),
        "source_unit_count": len(best_by_source),
        "best_source_failure_class_counts": failure_class_counts(list(best_by_source.values())),
        "best_source_error_pattern_counts": count_values(
            [row.get("error_pattern") for row in best_by_source.values()]
        ),
        "best_sources": list(best_by_source.values()),
        "coverage_status_counts": count_values(coverage_values),
        "examples_by_class": merge_example_buckets(
            run_summaries, max_examples_per_class=max_examples_per_class
        ),
        "runs": run_summaries,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "roots",
        nargs="*",
        type=Path,
        default=DEFAULT_ROOTS,
        help="Run root directories or verification-results.json files to summarize.",
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-examples-per-class", type=int, default=5)
    args = parser.parse_args()
    summary = summarize_roots(args.roots, max_examples_per_class=args.max_examples_per_class)
    write_json(args.output, summary)
    print(json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=False))


if __name__ == "__main__":
    main()
