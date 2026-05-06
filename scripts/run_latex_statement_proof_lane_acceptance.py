#!/usr/bin/env python3
"""Overlay and verify target-hidden proof-lane solution outputs."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.compare_latex_statement_generation_to_gold import compare as exact_compare  # noqa: E402
from scripts.merge_latex_statement_generation_units import run as merge_run  # noqa: E402
from scripts.run_latex_statement_generation import write_json  # noqa: E402
from scripts.run_latex_statement_generation_repair import load_generation_output  # noqa: E402
from scripts.verify_latex_statement_generation import DEFAULT_IMPORTS, DEFAULT_OPENS  # noqa: E402
from scripts.verify_latex_statement_generation import REPO_ROOT as VERIFY_REPO_ROOT  # noqa: E402
from scripts.verify_latex_statement_generation import run as verify_run  # noqa: E402
from scripts.verify_latex_statement_semantic_coverage import compare as semantic_compare  # noqa: E402


FORBIDDEN_TASK_PATTERNS = (
    "posthoc_lean_alignment",
    "aligned_lean",
    "aligned_gold",
    "semantic_passed_gold",
    "gold_full_name",
)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def unique_in_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value and value not in seen:
            out.append(value)
            seen.add(value)
    return out


def proof_lane_task_keys(task_dir: Path) -> list[str]:
    summary_path = task_dir / "proof-lane-summary.json"
    if summary_path.exists():
        summary = read_json(summary_path)
        keys = [str(key) for key in summary.get("unit_keys") or [] if key]
        if keys:
            return unique_in_order(keys)

    keys: list[str] = []
    for row in read_jsonl(task_dir / "proof-lane-tasks.jsonl"):
        keys.append(str(row.get("unit_key") or ""))
    for path in sorted((task_dir / "tasks").glob("*.json")):
        try:
            keys.append(str(read_json(path).get("unit_key") or ""))
        except (OSError, json.JSONDecodeError):
            continue
    return unique_in_order(keys)


def solution_unit_keys(solution_runs: list[Path]) -> list[str]:
    keys: list[str] = []
    for run_path in solution_runs:
        output = load_generation_output(run_path)
        keys.extend(str(unit.get("unit_key") or "") for unit in output.get("units") or [])
    return unique_in_order(keys)


def scan_task_leakage(task_dir: Path) -> list[dict[str, str]]:
    regexes = [(pattern, re.compile(re.escape(pattern))) for pattern in FORBIDDEN_TASK_PATTERNS]
    matches: list[dict[str, str]] = []
    for path in sorted(task_dir.rglob("*")):
        if not path.is_file() or path.suffix not in {".json", ".jsonl", ".md", ".txt"}:
            continue
        text = path.read_text(encoding="utf-8")
        for pattern, regex in regexes:
            if regex.search(text):
                matches.append({"path": str(path), "pattern": pattern})
    return matches


def units_from_verification(summary: dict[str, Any]) -> dict[str, dict[str, Any]]:
    units: dict[str, dict[str, Any]] = {}
    for batch in summary.get("batches") or []:
        for unit in batch.get("units") or []:
            unit_key = str(unit.get("unit_key") or "")
            if unit_key:
                units[unit_key] = unit
    return units


def units_from_coverage(summary: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not summary:
        return {}
    return {
        str(unit.get("unit_key") or ""): unit
        for unit in summary.get("units") or []
        if unit.get("unit_key")
    }


def compact_unit_results(
    *,
    solution_keys: list[str],
    verification_summary: dict[str, Any],
    semantic_summary: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    verification_by_key = units_from_verification(verification_summary)
    semantic_by_key = units_from_coverage(semantic_summary)
    results: list[dict[str, Any]] = []
    for unit_key in solution_keys:
        verification = verification_by_key.get(unit_key, {})
        semantic = semantic_by_key.get(unit_key, {})
        results.append(
            {
                "unit_key": unit_key,
                "compile_passed": verification.get("compile_passed"),
                "failure_class": verification.get("failure_class"),
                "reported_status": verification.get("reported_status"),
                "semantic_coverage_status": semantic.get("coverage_status"),
                "semantic_passed_gold_declarations": semantic.get("semantic_passed_gold_declarations"),
                "aligned_gold_declaration_count": semantic.get("aligned_gold_declaration_count"),
            }
        )
    return results


def count_key(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    return dict(sorted(Counter(str(row.get(key) or "unknown") for row in rows).items()))


def markdown_summary(summary: dict[str, Any]) -> str:
    lines = [
        "# Proof-Lane Acceptance Summary",
        "",
        f"- Base generation run: `{summary['base_generation_run']}`",
        f"- Proof-lane task dir: `{summary['proof_lane_task_dir']}`",
        f"- Output run: `{summary['output']}`",
        f"- Solution units: `{', '.join(summary['solution_unit_keys'])}`",
        f"- Verification compile: `{summary['verification']['compile_passed_units']}/{summary['verification']['unit_count']}`",
        f"- Verification failure classes: `{summary['verification']['failure_class_counts']}`",
    ]
    semantic = summary.get("semantic_coverage")
    if semantic:
        lines.extend(
            [
                f"- Semantic coverage: `{semantic['all_aligned_gold_proved_units']}/{semantic['unit_count']}` all aligned gold proved",
                f"- Semantic status counts: `{semantic['coverage_status_counts']}`",
            ]
        )
    else:
        lines.append("- Semantic coverage: `not run`")
    lines.extend(
        [
            "",
            "## Solution Unit Results",
            "",
            "| Unit | Compile | Failure class | Semantic status |",
            "|---|---:|---|---|",
        ]
    )
    for row in summary["solution_unit_results"]:
        lines.append(
            "| {unit_key} | {compile_passed} | `{failure_class}` | `{semantic_coverage_status}` |".format(
                unit_key=row["unit_key"],
                compile_passed=row.get("compile_passed"),
                failure_class=row.get("failure_class"),
                semantic_coverage_status=row.get("semantic_coverage_status"),
            )
        )
    lines.extend(
        [
            "",
            "Caveat: semantic/exact gold checks are post-hoc grader-only checks. They are not proof-lane prompt context.",
            "",
        ]
    )
    return "\n".join(lines)


def run(args: argparse.Namespace) -> dict[str, Any]:
    task_keys = proof_lane_task_keys(args.proof_lane_task_dir)
    if not task_keys:
        raise ValueError(f"no proof-lane task unit keys found under {args.proof_lane_task_dir}")

    solution_keys = solution_unit_keys(args.solution_generation_run)
    if not solution_keys:
        raise ValueError("proof-lane solution runs did not contain any units")

    unexpected_keys = sorted(set(solution_keys) - set(task_keys))
    if unexpected_keys:
        raise ValueError(
            "proof-lane solution contains unit keys not present in target-hidden task set: "
            + ", ".join(unexpected_keys)
        )

    leakage_matches = [] if args.allow_task_leakage else scan_task_leakage(args.proof_lane_task_dir)
    if leakage_matches:
        first = ", ".join(f"{match['path']}:{match['pattern']}" for match in leakage_matches[:5])
        raise ValueError(f"proof-lane task directory contains forbidden post-hoc metadata patterns: {first}")

    args.output.mkdir(parents=True, exist_ok=True)
    eval_dir = args.output / "eval"
    eval_dir.mkdir(exist_ok=True)

    merge_summary = merge_run(
        argparse.Namespace(
            base_generation_run=args.base_generation_run,
            overlay_generation_run=args.solution_generation_run,
            output=args.output,
        )
    )

    verification_path = eval_dir / "verification-results.json"
    verification_summary = verify_run(
        argparse.Namespace(
            generation_run=args.output,
            project_root=args.project_root,
            imports=args.imports,
            opens=args.opens,
            infer_context=args.infer_context,
            filter_target_module_imports=args.filter_target_module_imports,
            validate_inferred_opens=args.validate_inferred_opens,
            timeout_seconds=args.timeout_seconds,
            open_timeout_seconds=args.open_timeout_seconds,
            materialize_visible_support=args.materialize_visible_support,
            support_timeout_seconds=args.support_timeout_seconds,
            output=verification_path,
        )
    )

    selector_run = args.selector_run or (Path(merge_summary["selector_run"]) if merge_summary.get("selector_run") else None)
    exact_summary: dict[str, Any] | None = None
    semantic_summary: dict[str, Any] | None = None
    exact_path: Path | None = None
    semantic_path: Path | None = None
    if selector_run:
        exact_path = eval_dir / "gold-comparison.json"
        exact_summary = exact_compare(selector_run, args.output, verification_path=verification_path)
        write_json(exact_path, exact_summary)
        if args.semantic_coverage:
            semantic_path = eval_dir / "semantic-coverage.json"
            semantic_summary = semantic_compare(
                argparse.Namespace(
                    selector_run=selector_run,
                    generation_run=args.output,
                    verification_results=verification_path,
                    run_uncompiled=False,
                    project_root=args.project_root,
                    timeout_seconds=args.timeout_seconds,
                    output=semantic_path,
                )
            )
            write_json(semantic_path, semantic_summary)

    solution_results = compact_unit_results(
        solution_keys=solution_keys,
        verification_summary=verification_summary,
        semantic_summary=semantic_summary,
    )
    summary = {
        "schema_version": "repoprover.latex_statement_proof_lane_acceptance.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "base_generation_run": str(args.base_generation_run),
        "proof_lane_task_dir": str(args.proof_lane_task_dir),
        "proof_lane_task_unit_keys": task_keys,
        "solution_generation_runs": [str(path) for path in args.solution_generation_run],
        "solution_unit_keys": solution_keys,
        "output": str(args.output),
        "merge_summary": str(eval_dir / "merge-summary.json"),
        "verification_results": str(verification_path),
        "gold_comparison": str(exact_path) if exact_path else None,
        "semantic_coverage_results": str(semantic_path) if semantic_path else None,
        "selector_run": str(selector_run) if selector_run else None,
        "no_paid_call_made": True,
        "task_leakage_scan": {
            "enabled": not args.allow_task_leakage,
            "forbidden_patterns": list(FORBIDDEN_TASK_PATTERNS),
            "matches": leakage_matches,
        },
        "verification": {
            "compile_passed_units": verification_summary.get("compile_passed_units"),
            "unit_count": verification_summary.get("unit_count"),
            "failure_class_counts": verification_summary.get("failure_class_counts", {}),
        },
        "gold_comparison_summary": (
            {
                "coverage_status_counts": exact_summary.get("coverage_status_counts", {}),
                "compiled_name_overlap_units": exact_summary.get("compiled_name_overlap_units"),
                "compiled_needs_semantic_review_units": exact_summary.get("compiled_needs_semantic_review_units"),
            }
            if exact_summary
            else None
        ),
        "semantic_coverage": (
            {
                "all_aligned_gold_proved_units": semantic_summary.get("all_aligned_gold_proved_units"),
                "unit_count": semantic_summary.get("unit_count"),
                "coverage_status_counts": semantic_summary.get("coverage_status_counts", {}),
            }
            if semantic_summary
            else None
        ),
        "solution_unit_results": solution_results,
        "solution_failure_class_counts": count_key(solution_results, "failure_class"),
        "solution_semantic_status_counts": count_key(solution_results, "semantic_coverage_status"),
    }
    write_json(eval_dir / "proof-lane-acceptance-summary.json", summary)
    (eval_dir / "proof-lane-acceptance-summary.md").write_text(markdown_summary(summary), encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-generation-run", type=Path, required=True)
    parser.add_argument("--proof-lane-task-dir", type=Path, required=True)
    parser.add_argument("--solution-generation-run", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--selector-run", type=Path)
    parser.add_argument("--project-root", type=Path, default=VERIFY_REPO_ROOT / "algebraic-combinatorics")
    parser.add_argument("--imports", nargs="+", default=DEFAULT_IMPORTS)
    parser.add_argument("--opens", nargs="*", default=DEFAULT_OPENS)
    parser.add_argument("--no-infer-context", dest="infer_context", action="store_false")
    parser.set_defaults(infer_context=True)
    parser.add_argument("--allow-target-module-imports", dest="filter_target_module_imports", action="store_false")
    parser.set_defaults(filter_target_module_imports=True)
    parser.add_argument("--no-validate-inferred-opens", dest="validate_inferred_opens", action="store_false")
    parser.set_defaults(validate_inferred_opens=True)
    parser.add_argument("--timeout-seconds", type=float, default=120.0)
    parser.add_argument("--open-timeout-seconds", type=float, default=30.0)
    parser.add_argument("--no-materialize-visible-support", dest="materialize_visible_support", action="store_false")
    parser.set_defaults(materialize_visible_support=True)
    parser.add_argument("--support-timeout-seconds", type=float, default=30.0)
    parser.add_argument("--no-semantic-coverage", dest="semantic_coverage", action="store_false")
    parser.set_defaults(semantic_coverage=True)
    parser.add_argument(
        "--allow-task-leakage",
        action="store_true",
        help="Disable the task-directory post-hoc metadata pattern scan. Intended only for debugging bad artifacts.",
    )
    args = parser.parse_args()
    print(json.dumps(run(args), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
