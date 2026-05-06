#!/usr/bin/env python3
"""Run a bounded theorem-level context-selection and repair loop.

This orchestrates the manual loop used in the symmetric ``e_n = 0`` probe:
repair-context selection, Mathlib hydration, checked context-pack construction,
generation repair, Lean verification, and optional post-hoc gold/semantic
grading. The selector/generator stages remain source-only; gold is used only by
optional graders after verification.
"""

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

from scripts.build_latex_statement_repair_context_pack import run as run_context_pack  # noqa: E402
from scripts.compare_latex_statement_generation_to_gold import compare as compare_to_gold  # noqa: E402
from scripts.compare_latex_statement_generation_to_gold import write_json as write_json  # noqa: E402
from scripts.hydrate_latex_statement_context import (  # noqa: E402
    DEFAULT_IMPORTS as HYDRATION_DEFAULT_IMPORTS,
)
from scripts.hydrate_latex_statement_context import (  # noqa: E402
    DEFAULT_OPENS as HYDRATION_DEFAULT_OPENS,
)
from scripts.hydrate_latex_statement_context import run as run_hydration  # noqa: E402
from scripts.run_latex_statement_generation import DEFAULT_BASE_URL, DEFAULT_MODEL  # noqa: E402
from scripts.run_latex_statement_generation_repair import run as run_repair  # noqa: E402
from scripts.run_latex_statement_repair_context_selection import run as run_context_selection  # noqa: E402
from scripts.verify_latex_statement_generation import (  # noqa: E402
    DEFAULT_IMPORTS as VERIFICATION_DEFAULT_IMPORTS,
)
from scripts.verify_latex_statement_generation import (  # noqa: E402
    DEFAULT_OPENS as VERIFICATION_DEFAULT_OPENS,
)
from scripts.verify_latex_statement_generation import run as run_verification  # noqa: E402
from scripts.verify_latex_statement_semantic_coverage import compare as semantic_compare  # noqa: E402


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def all_units_compile(verification: dict[str, Any]) -> bool:
    unit_count = int(verification.get("unit_count") or 0)
    return unit_count > 0 and int(verification.get("compile_passed_units") or 0) == unit_count


def generation_output_path(run_dir: Path) -> Path:
    path = run_dir / "batch-001" / "generation-output.json"
    if not path.exists():
        raise FileNotFoundError(path)
    return path


def compile_clean_unit_keys(verification: dict[str, Any]) -> set[str]:
    keys: set[str] = set()
    for batch in verification.get("batches") or []:
        for unit in batch.get("units") or []:
            if unit.get("compile_passed") and unit.get("unit_key"):
                keys.add(str(unit["unit_key"]))
    return keys


def preserve_compile_clean_units(
    *,
    previous_generation_run: Path,
    previous_verification_results: Path,
    repair_run: Path,
    preserve_unit_keys: set[str] | None = None,
) -> dict[str, Any]:
    previous_verification = read_json(previous_verification_results)
    clean_keys = compile_clean_unit_keys(previous_verification)
    if preserve_unit_keys is not None:
        clean_keys &= preserve_unit_keys
    if not clean_keys:
        return {"preserved_unit_keys": [], "updated_paths": []}

    previous_output = read_json(generation_output_path(previous_generation_run))
    repair_output_path = generation_output_path(repair_run)
    repair_output = read_json(repair_output_path)

    previous_units = {str(unit.get("unit_key") or ""): unit for unit in previous_output.get("units") or []}
    repair_units = {str(unit.get("unit_key") or ""): unit for unit in repair_output.get("units") or []}
    merged_units: list[dict[str, Any]] = []
    seen: set[str] = set()
    for previous_unit in previous_output.get("units") or []:
        unit_key = str(previous_unit.get("unit_key") or "")
        if unit_key in clean_keys:
            merged_units.append(previous_unit)
        else:
            merged_units.append(repair_units.get(unit_key, previous_unit))
        seen.add(unit_key)
    for unit_key, unit in repair_units.items():
        if unit_key not in seen:
            merged_units.append(unit)
    merged_output = dict(repair_output)
    merged_output["units"] = merged_units

    updated_paths: list[str] = []
    for name in ("generation-output.json", "repair-output.json"):
        path = repair_run / "batch-001" / name
        if path.exists():
            write_json(path, merged_output)
            updated_paths.append(str(path))
    return {
        "preserved_unit_keys": sorted(clean_keys.intersection(previous_units)),
        "updated_paths": updated_paths,
    }


def run_gold_graders(
    *,
    selector_run: Path,
    generation_run: Path,
    verification_results: Path,
    project_root: Path,
    timeout_seconds: float,
    semantic_coverage: bool,
) -> dict[str, Any]:
    eval_dir = generation_run / "eval"
    gold_summary = compare_to_gold(
        selector_run,
        generation_run,
        verification_path=verification_results,
    )
    write_json(eval_dir / "gold-comparison.json", gold_summary)
    result: dict[str, Any] = {"gold_comparison": str(eval_dir / "gold-comparison.json")}
    if semantic_coverage:
        semantic_args = argparse.Namespace(
            selector_run=selector_run,
            generation_run=generation_run,
            verification_results=verification_results,
            run_uncompiled=False,
            project_root=project_root,
            timeout_seconds=timeout_seconds,
            output=eval_dir / "semantic-coverage.json",
        )
        semantic_summary = semantic_compare(semantic_args)
        write_json(eval_dir / "semantic-coverage.json", semantic_summary)
        result["semantic_coverage"] = str(eval_dir / "semantic-coverage.json")
    return result


def semantic_source_coverage_review_keys(semantic_summary: dict[str, Any]) -> set[str]:
    keys: set[str] = set()
    for unit in semantic_summary.get("units") or []:
        if unit.get("coverage_status") != "all_aligned_gold_proved" and unit.get("unit_key"):
            keys.add(str(unit["unit_key"]))
    return keys


def semantic_success_keys(semantic_summary: dict[str, Any]) -> set[str]:
    keys: set[str] = set()
    for unit in semantic_summary.get("units") or []:
        if unit.get("coverage_status") == "all_aligned_gold_proved" and unit.get("unit_key"):
            keys.add(str(unit["unit_key"]))
    return keys


def run(args: argparse.Namespace) -> dict[str, Any]:
    output_root = args.output_root
    output_root.mkdir(parents=True, exist_ok=True)

    current_generation_run = args.initial_generation_run
    current_verification_results = args.initial_verification_results
    accumulated_contexts = list(args.extra_context or [])
    source_coverage_review_keys: set[str] = set()
    preserve_unit_keys: set[str] | None = None
    if args.initial_semantic_coverage_results:
        initial_semantic = read_json(args.initial_semantic_coverage_results)
        source_coverage_review_keys = semantic_source_coverage_review_keys(initial_semantic)
        preserve_unit_keys = semantic_success_keys(initial_semantic)
    rounds: list[dict[str, Any]] = []
    stop_reason = "max_rounds_reached"

    for round_index in range(1, args.max_rounds + 1):
        context_run = output_root / f"round-{round_index:02d}-context"
        repair_run = output_root / f"round-{round_index:02d}-repair"
        checked_pack = context_run / "checked-repair-context.json"

        context_summary = run_context_selection(
            argparse.Namespace(
                selector_run=args.selector_run,
                generation_run=current_generation_run,
                verification_results=current_verification_results,
                source_coverage_review_unit_key=sorted(source_coverage_review_keys),
                output=context_run,
                model=args.model,
                base_url=args.base_url,
                max_tokens=args.max_tokens,
                temperature=args.temperature,
                reasoning_effort=args.reasoning_effort,
                budget_only=args.budget_only,
            )
        )
        round_summary: dict[str, Any] = {
            "round": round_index,
            "input_generation_run": str(current_generation_run),
            "input_verification_results": str(current_verification_results),
            "context_run": str(context_run),
            "context_selection": context_summary,
        }
        rounds.append(round_summary)
        if args.budget_only:
            stop_reason = "budget_only_after_context_selection"
            break

        hydration_summary = run_hydration(
            argparse.Namespace(
                run=context_run,
                project_root=args.project_root,
                imports=args.hydration_imports,
                opens=args.hydration_opens,
                timeout_seconds=args.timeout_seconds,
                summary=context_run / "eval" / "mathlib-hydration-summary.json",
            )
        )
        pack_summary = run_context_pack(
            argparse.Namespace(
                repair_context_run=context_run,
                output=checked_pack,
            )
        )
        accumulated_contexts.append(checked_pack)

        repair_summary = run_repair(
            argparse.Namespace(
                selector_run=args.selector_run,
                generation_run=current_generation_run,
                verification_results=current_verification_results,
                extra_context=list(accumulated_contexts),
                output=repair_run,
                model=args.model,
                base_url=args.base_url,
                max_tokens=args.max_tokens,
                temperature=args.temperature,
                reasoning_effort=args.reasoning_effort,
                budget_only=False,
            )
        )
        preservation_summary = preserve_compile_clean_units(
            previous_generation_run=current_generation_run,
            previous_verification_results=current_verification_results,
            repair_run=repair_run,
            preserve_unit_keys=preserve_unit_keys,
        )
        verification_path = repair_run / "eval" / "verification-results.json"
        verification_summary = run_verification(
            argparse.Namespace(
                generation_run=repair_run,
                project_root=args.project_root,
                imports=args.verification_imports,
                opens=args.verification_opens,
                infer_context=True,
                materialize_visible_support=args.materialize_visible_support,
                timeout_seconds=args.timeout_seconds,
                output=verification_path,
            )
        )

        round_summary.update(
            {
                "hydration": hydration_summary,
                "checked_repair_context": str(checked_pack),
                "checked_repair_context_summary": pack_summary,
                "repair_run": str(repair_run),
                "repair": repair_summary,
                "preserve_compile_clean_units": preservation_summary,
                "verification_results": str(verification_path),
                "verification": verification_summary,
            }
        )
        if all_units_compile(verification_summary):
            grader_paths = run_gold_graders(
                selector_run=args.selector_run,
                generation_run=repair_run,
                verification_results=verification_path,
                project_root=args.project_root,
                timeout_seconds=args.timeout_seconds,
                semantic_coverage=args.semantic_coverage,
            )
            round_summary["posthoc_graders"] = grader_paths
            current_generation_run = repair_run
            current_verification_results = verification_path
            if args.semantic_coverage:
                semantic_path = repair_run / "eval" / "semantic-coverage.json"
                semantic_summary = read_json(semantic_path)
                source_coverage_review_keys = semantic_source_coverage_review_keys(semantic_summary)
                preserve_unit_keys = semantic_success_keys(semantic_summary)
                round_summary["source_coverage_review_unit_keys"] = sorted(source_coverage_review_keys)
                round_summary["semantic_success_unit_keys"] = sorted(preserve_unit_keys)
                if not source_coverage_review_keys:
                    stop_reason = "all_units_semantically_covered"
                    break
                stop_reason = "semantic_coverage_incomplete"
                continue
            stop_reason = "all_units_compile"
            break

        current_generation_run = repair_run
        current_verification_results = verification_path

    summary = {
        "schema_version": "repoprover.latex_statement_repair_loop.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "selector_run": str(args.selector_run),
        "initial_generation_run": str(args.initial_generation_run),
        "initial_verification_results": str(args.initial_verification_results),
        "initial_semantic_coverage_results": (
            str(args.initial_semantic_coverage_results) if args.initial_semantic_coverage_results else None
        ),
        "output_root": str(output_root),
        "model": args.model,
        "reasoning_effort": args.reasoning_effort,
        "max_rounds": args.max_rounds,
        "budget_only": args.budget_only,
        "semantic_coverage": args.semantic_coverage,
        "materialize_visible_support": args.materialize_visible_support,
        "stop_reason": stop_reason,
        "final_generation_run": str(current_generation_run),
        "final_verification_results": str(current_verification_results),
        "rounds": rounds,
    }
    write_json(output_root / "repair-loop-summary.json", summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selector-run", type=Path, required=True)
    parser.add_argument("--initial-generation-run", type=Path, required=True)
    parser.add_argument("--initial-verification-results", type=Path, required=True)
    parser.add_argument(
        "--initial-semantic-coverage-results",
        type=Path,
        help=(
            "Optional semantic-coverage JSON for resuming from a compile-clean but source-coverage-partial run. "
            "Only unit keys are used to decide which source units need review; gold statements are not added to prompts."
        ),
    )
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--max-rounds", type=int, default=3)
    parser.add_argument("--extra-context", type=Path, action="append")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--max-tokens", type=int, default=4096)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--reasoning-effort", default="none")
    parser.add_argument("--project-root", type=Path, default=REPO_ROOT / "algebraic-combinatorics")
    parser.add_argument("--hydration-imports", nargs="+", default=HYDRATION_DEFAULT_IMPORTS)
    parser.add_argument("--hydration-opens", nargs="*", default=HYDRATION_DEFAULT_OPENS)
    parser.add_argument("--verification-imports", nargs="+", default=VERIFICATION_DEFAULT_IMPORTS)
    parser.add_argument("--verification-opens", nargs="*", default=VERIFICATION_DEFAULT_OPENS)
    parser.add_argument(
        "--materialize-visible-support",
        action="store_true",
        help=(
            "When verifying repair outputs, incrementally materialize prompt-visible "
            "project/local support snippets before the repaired generated body."
        ),
    )
    parser.add_argument("--timeout-seconds", type=float, default=120.0)
    parser.add_argument("--semantic-coverage", action="store_true")
    parser.add_argument("--budget-only", action="store_true")
    args = parser.parse_args()
    print(json.dumps(run(args), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
