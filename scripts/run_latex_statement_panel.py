#!/usr/bin/env python3
"""Run a fixed LaTeX-statement panel through the theorem-level pipeline.

The runner is intentionally thin: it calls the existing selector, hydrator,
generator, verifier, and post-hoc comparison scripts, then writes a compact
summary. It makes panel runs repeatable without hiding the stage artifacts that
are needed for audit and debugging.
"""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PANEL = REPO_ROOT / "docs/latex-statement-dev-panel-2026-05-06.json"
DEFAULT_MODEL = "deepseek/deepseek-v4-flash"
DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def load_panel_unit_ids(path: Path) -> list[str]:
    panel = read_json(path)
    unit_ids = panel.get("unit_ids")
    if unit_ids is None:
        unit_ids = [unit.get("id") for unit in panel.get("units") or []]
    if not isinstance(unit_ids, list):
        raise ValueError(f"{path}: expected `unit_ids` to be a list")
    cleaned = [str(unit_id) for unit_id in unit_ids if str(unit_id or "").strip()]
    if not cleaned:
        raise ValueError(f"{path}: no panel unit ids found")
    duplicates = sorted({unit_id for unit_id in cleaned if cleaned.count(unit_id) > 1})
    if duplicates:
        raise ValueError(f"{path}: duplicate panel unit ids: {duplicates}")
    return cleaned


def append_reasoning_flag(command: list[str], value: str | None) -> None:
    if value and value != "default":
        command.extend(["--reasoning-effort", value])


def command_text(command: list[str]) -> str:
    return shlex.join(command)


def tail_text(text: str, limit: int = 4000) -> str:
    if len(text) <= limit:
        return text
    return text[-limit:]


def run_command(stage: str, command: list[str], *, output_root: Path) -> dict[str, Any]:
    logs_dir = output_root / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    completed = subprocess.run(command, cwd=REPO_ROOT, text=True, capture_output=True)
    elapsed = round(time.monotonic() - started, 3)
    stdout_path = logs_dir / f"{stage}.stdout.log"
    stderr_path = logs_dir / f"{stage}.stderr.log"
    stdout_path.write_text(completed.stdout, encoding="utf-8")
    stderr_path.write_text(completed.stderr, encoding="utf-8")
    return {
        "stage": stage,
        "command": command_text(command),
        "exit_code": completed.returncode,
        "elapsed_seconds": elapsed,
        "stdout_log": str(stdout_path),
        "stderr_log": str(stderr_path),
        "stdout_tail": tail_text(completed.stdout),
        "stderr_tail": tail_text(completed.stderr),
    }


def cost_from_summary(summary: dict[str, Any]) -> float:
    cost_summary = summary.get("cost_summary") or {}
    value = cost_summary.get("openrouter_reported_cost")
    if value is None:
        usage = cost_summary.get("usage") or {}
        value = usage.get("cost")
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


def usage_totals(summary: dict[str, Any]) -> dict[str, int] | None:
    cost_summary = summary.get("cost_summary") or {}
    usage = cost_summary.get("usage")
    if isinstance(usage, dict):
        details = usage.get("completion_tokens_details") or {}
        prompt_details = usage.get("prompt_tokens_details") or {}
        return {
            "prompt_tokens": int(usage.get("prompt_tokens") or 0),
            "completion_tokens": int(usage.get("completion_tokens") or 0),
            "reasoning_tokens": int(details.get("reasoning_tokens") or 0),
            "cached_prompt_tokens": int(prompt_details.get("cached_tokens") or 0),
        }
    batch_summaries = cost_summary.get("batches")
    if not isinstance(batch_summaries, list):
        return None
    totals = {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "reasoning_tokens": 0,
        "cached_prompt_tokens": 0,
    }
    saw_usage = False
    for batch in batch_summaries:
        batch_usage = (batch or {}).get("usage") or {}
        if not batch_usage:
            continue
        saw_usage = True
        details = batch_usage.get("completion_tokens_details") or {}
        prompt_details = batch_usage.get("prompt_tokens_details") or {}
        totals["prompt_tokens"] += int(batch_usage.get("prompt_tokens") or 0)
        totals["completion_tokens"] += int(batch_usage.get("completion_tokens") or 0)
        totals["reasoning_tokens"] += int(details.get("reasoning_tokens") or 0)
        totals["cached_prompt_tokens"] += int(prompt_details.get("cached_tokens") or 0)
    return totals if saw_usage else None


def summarize_context_selection(path: Path) -> dict[str, Any] | None:
    summary_path = path / "eval" / "context-selection-results.json"
    if not summary_path.exists():
        return None
    summary = read_json(summary_path)
    usage = usage_totals(summary) or {}
    return {
        "path": str(path),
        "budget_only": summary.get("budget_only"),
        "paid_call_made": summary.get("paid_call_made"),
        "valid_json": summary.get("valid_json"),
        "elapsed_seconds": summary.get("elapsed_seconds"),
        "cost": cost_from_summary(summary),
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
        "reasoning_tokens": usage.get("reasoning_tokens"),
        "cached_prompt_tokens": usage.get("cached_prompt_tokens"),
        "units_selected": summary.get("units_selected"),
    }


def summarize_hydration(path: Path) -> dict[str, Any] | None:
    summary_path = path / "eval" / "mathlib-hydration-summary.json"
    if not summary_path.exists():
        return None
    summary = read_json(summary_path)
    batches = summary.get("batches") or []
    return {
        "path": str(summary_path),
        "batch_count": len(batches),
        "request_count": sum(int(batch.get("request_count") or 0) for batch in batches),
        "exact_identifier_count": sum(int(batch.get("exact_identifier_count") or 0) for batch in batches),
        "fallback_exact_identifier_count": sum(
            int(batch.get("fallback_exact_identifier_count") or 0) for batch in batches
        ),
        "lean_check_statuses": [batch.get("lean_check_status") for batch in batches],
        "fallback_lean_check_statuses": [batch.get("fallback_lean_check_status") for batch in batches],
    }


def summarize_generation(path: Path) -> dict[str, Any] | None:
    summary_path = path / "eval" / "generation-results.json"
    if not summary_path.exists():
        return None
    summary = read_json(summary_path)
    usage = usage_totals(summary) or {}
    normalized_units = 0
    for batch in summary.get("batches") or []:
        normalized_units += int((batch.get("contract_enforcement") or {}).get("normalized_unit_count") or 0)
    return {
        "path": str(path),
        "budget_only": summary.get("budget_only"),
        "paid_call_made": summary.get("paid_call_made"),
        "valid_json": summary.get("valid_json"),
        "elapsed_seconds": summary.get("elapsed_seconds"),
        "cost": cost_from_summary(summary),
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
        "reasoning_tokens": usage.get("reasoning_tokens"),
        "cached_prompt_tokens": usage.get("cached_prompt_tokens"),
        "batch_count": summary.get("batch_count"),
        "normalized_unit_count": normalized_units,
    }


def summarize_verification(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    summary = read_json(path)
    return {
        "path": str(path),
        "unit_count": summary.get("unit_count"),
        "compile_passed_units": summary.get("compile_passed_units"),
        "failure_class_counts": summary.get("failure_class_counts", {}),
        "materialize_visible_support": summary.get("materialize_visible_support"),
    }


def summarize_gold(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    summary = read_json(path)
    return {
        "path": str(path),
        "unit_count": summary.get("unit_count"),
        "compile_passed_units": summary.get("compile_passed_units"),
        "compiled_name_overlap_units": summary.get("compiled_name_overlap_units"),
        "compiled_needs_semantic_review_units": summary.get("compiled_needs_semantic_review_units"),
        "coverage_status_counts": summary.get("coverage_status_counts", {}),
    }


def summarize_semantic(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    summary = read_json(path)
    return {
        "path": str(path),
        "unit_count": summary.get("unit_count"),
        "all_aligned_gold_proved_units": summary.get("all_aligned_gold_proved_units"),
        "coverage_status_counts": summary.get("coverage_status_counts", {}),
    }


def run_stage(summary: dict[str, Any], stage: str, command: list[str], output_root: Path) -> bool:
    result = run_command(stage, command, output_root=output_root)
    summary.setdefault("stages", []).append(result)
    if result["exit_code"] != 0:
        summary["stop_reason"] = f"{stage}_failed"
        return False
    return True


def build_selector_command(args: argparse.Namespace, unit_ids: list[str], selector_run: Path) -> list[str]:
    command = [
        sys.executable,
        "scripts/run_latex_statement_context_selection.py",
        "--output",
        str(selector_run),
        "--model",
        args.selector_model,
        "--base-url",
        args.base_url,
        "--max-tokens",
        str(args.selector_max_tokens),
        "--temperature",
        str(args.selector_temperature),
    ]
    for unit_id in unit_ids:
        command.extend(["--unit-id", unit_id])
    append_reasoning_flag(command, args.selector_reasoning_effort)
    if args.budget_only or args.selector_budget_only:
        command.append("--budget-only")
    return command


def build_hydration_command(args: argparse.Namespace, selector_run: Path) -> list[str]:
    return [
        sys.executable,
        "scripts/hydrate_latex_statement_context.py",
        "--run",
        str(selector_run),
        "--project-root",
        str(args.project_root),
        "--timeout-seconds",
        str(args.hydration_timeout_seconds),
        "--summary",
        str(selector_run / "eval" / "mathlib-hydration-summary.json"),
    ]


def build_generation_command(args: argparse.Namespace, selector_run: Path, generation_run: Path) -> list[str]:
    command = [
        sys.executable,
        "scripts/run_latex_statement_generation.py",
        "--selector-run",
        str(selector_run),
        "--output",
        str(generation_run),
        "--model",
        args.generation_model,
        "--base-url",
        args.base_url,
        "--max-tokens",
        str(args.generation_max_tokens),
        "--temperature",
        str(args.generation_temperature),
        "--max-units-per-call",
        str(args.max_units_per_call),
    ]
    append_reasoning_flag(command, args.generation_reasoning_effort)
    if args.generation_budget_only:
        command.append("--budget-only")
    return command


def build_verification_command(args: argparse.Namespace, generation_run: Path, output: Path) -> list[str]:
    command = [
        sys.executable,
        "scripts/verify_latex_statement_generation.py",
        "--generation-run",
        str(generation_run),
        "--project-root",
        str(args.project_root),
        "--timeout-seconds",
        str(args.verification_timeout_seconds),
        "--output",
        str(output),
    ]
    if args.materialize_visible_support:
        command.append("--materialize-visible-support")
        command.extend(["--support-timeout-seconds", str(args.support_timeout_seconds)])
    return command


def build_gold_command(selector_run: Path, generation_run: Path, verification_results: Path, output: Path) -> list[str]:
    return [
        sys.executable,
        "scripts/compare_latex_statement_generation_to_gold.py",
        "--selector-run",
        str(selector_run),
        "--generation-run",
        str(generation_run),
        "--verification-results",
        str(verification_results),
        "--output",
        str(output),
    ]


def build_semantic_command(
    args: argparse.Namespace,
    selector_run: Path,
    generation_run: Path,
    verification_results: Path,
    output: Path,
) -> list[str]:
    command = [
        sys.executable,
        "scripts/verify_latex_statement_semantic_coverage.py",
        "--selector-run",
        str(selector_run),
        "--generation-run",
        str(generation_run),
        "--verification-results",
        str(verification_results),
        "--project-root",
        str(args.project_root),
        "--timeout-seconds",
        str(args.semantic_timeout_seconds),
        "--output",
        str(output),
    ]
    if args.run_semantic_uncompiled:
        command.append("--run-uncompiled")
    return command


def render_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# LaTeX Statement Panel Run",
        "",
        f"- Generated: `{summary['generated_at']}`",
        f"- Panel: `{summary['panel']}`",
        f"- Output root: `{summary['output_root']}`",
        f"- Stop reason: `{summary.get('stop_reason')}`",
        f"- Unit count: {len(summary['unit_ids'])}",
        "",
        "## Stage Results",
        "",
        "| Stage | Exit | Seconds | Command |",
        "|---|---:|---:|---|",
    ]
    for stage in summary.get("stages", []):
        lines.append(
            f"| `{stage['stage']}` | {stage['exit_code']} | {stage['elapsed_seconds']} | "
            f"`{stage['command']}` |"
        )
    lines.extend(["", "## Metrics", "", "```json", json.dumps(summary.get("metrics", {}), indent=2), "```", ""])
    return "\n".join(lines)


def write_summary(output_root: Path, summary: dict[str, Any]) -> None:
    metrics = {
        "context_selection": summarize_context_selection(Path(summary["selector_run"])),
        "hydration": summarize_hydration(Path(summary["selector_run"])),
        "generation": summarize_generation(Path(summary["generation_run"])) if summary.get("generation_run") else None,
        "verification": summarize_verification(Path(summary["verification_results"]))
        if summary.get("verification_results")
        else None,
        "gold_comparison": summarize_gold(Path(summary["gold_comparison_results"]))
        if summary.get("gold_comparison_results")
        else None,
        "semantic_coverage": summarize_semantic(Path(summary["semantic_coverage_results"]))
        if summary.get("semantic_coverage_results")
        else None,
    }
    summary["metrics"] = metrics
    summary_path = output_root / "eval" / "panel-summary.json"
    write_json(summary_path, summary)
    (output_root / "eval" / "panel-summary.md").write_text(render_markdown(summary), encoding="utf-8")


def run(args: argparse.Namespace) -> dict[str, Any]:
    output_root = args.output
    output_root.mkdir(parents=True, exist_ok=True)
    unit_ids = load_panel_unit_ids(args.panel)
    selector_run = args.selector_run or (output_root / "context-selection")
    generation_run = args.generation_run or (output_root / "generation")
    verification_results = output_root / "eval" / "verification-results.json"
    gold_results = output_root / "eval" / "gold-comparison-results.json"
    semantic_results = output_root / "eval" / "semantic-coverage-results.json"
    summary: dict[str, Any] = {
        "schema_version": "repoprover.latex_statement_panel_run.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "panel": str(args.panel),
        "output_root": str(output_root),
        "unit_ids": unit_ids,
        "selector_run": str(selector_run),
        "generation_run": str(generation_run),
        "verification_results": str(verification_results),
        "gold_comparison_results": str(gold_results),
        "semantic_coverage_results": str(semantic_results) if args.semantic_coverage else None,
        "stages": [],
        "stop_reason": "not_started",
    }

    if args.selector_run is None:
        if not run_stage(summary, "context_selection", build_selector_command(args, unit_ids, selector_run), output_root):
            write_summary(output_root, summary)
            return summary
    else:
        summary["stages"].append(
            {
                "stage": "context_selection",
                "command": "reuse existing selector run",
                "exit_code": 0,
                "elapsed_seconds": 0.0,
                "stdout_log": None,
                "stderr_log": None,
                "stdout_tail": "",
                "stderr_tail": "",
            }
        )

    if args.budget_only or args.selector_budget_only:
        summary["stop_reason"] = "budget_only_after_context_selection"
        write_summary(output_root, summary)
        return summary

    if not args.skip_hydration:
        if not run_stage(summary, "hydration", build_hydration_command(args, selector_run), output_root):
            write_summary(output_root, summary)
            return summary

    if args.skip_generation:
        if args.generation_run is None:
            summary["stop_reason"] = "stopped_before_generation"
            summary["generation_run"] = None
            summary["verification_results"] = None
            summary["gold_comparison_results"] = None
            summary["semantic_coverage_results"] = None
            write_summary(output_root, summary)
            return summary
        summary["stages"].append(
            {
                "stage": "generation",
                "command": "reuse existing generation run",
                "exit_code": 0,
                "elapsed_seconds": 0.0,
                "stdout_log": None,
                "stderr_log": None,
                "stdout_tail": "",
                "stderr_tail": "",
            }
        )
    else:
        if not run_stage(summary, "generation", build_generation_command(args, selector_run, generation_run), output_root):
            write_summary(output_root, summary)
            return summary
        if args.generation_budget_only:
            summary["stop_reason"] = "budget_only_after_generation"
            summary["verification_results"] = None
            summary["gold_comparison_results"] = None
            summary["semantic_coverage_results"] = None
            write_summary(output_root, summary)
            return summary

    if not args.skip_verification:
        if not run_stage(
            summary,
            "verification",
            build_verification_command(args, generation_run, verification_results),
            output_root,
        ):
            write_summary(output_root, summary)
            return summary
    else:
        summary["verification_results"] = None

    if not args.skip_gold_comparison and summary.get("verification_results"):
        if not run_stage(
            summary,
            "gold_comparison",
            build_gold_command(selector_run, generation_run, verification_results, gold_results),
            output_root,
        ):
            write_summary(output_root, summary)
            return summary
    else:
        summary["gold_comparison_results"] = None

    if args.semantic_coverage and summary.get("verification_results"):
        if not run_stage(
            summary,
            "semantic_coverage",
            build_semantic_command(args, selector_run, generation_run, verification_results, semantic_results),
            output_root,
        ):
            write_summary(output_root, summary)
            return summary

    summary["stop_reason"] = "completed"
    write_summary(output_root, summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel", type=Path, default=DEFAULT_PANEL)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--selector-run", type=Path, help="Reuse an existing selector run instead of running selection.")
    parser.add_argument(
        "--generation-run",
        type=Path,
        help="Generation directory to create, or an existing generation directory when used with --skip-generation.",
    )
    parser.add_argument("--project-root", type=Path, default=REPO_ROOT / "algebraic-combinatorics")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--selector-model", default=DEFAULT_MODEL)
    parser.add_argument("--generation-model", default=DEFAULT_MODEL)
    parser.add_argument("--selector-max-tokens", type=int, default=8192)
    parser.add_argument("--generation-max-tokens", type=int, default=8192)
    parser.add_argument("--selector-temperature", type=float, default=0.0)
    parser.add_argument("--generation-temperature", type=float, default=0.0)
    parser.add_argument(
        "--selector-reasoning-effort",
        default="none",
        help="Use `default` to omit the OpenRouter reasoning override.",
    )
    parser.add_argument(
        "--generation-reasoning-effort",
        default="none",
        help="Use `default` to omit the OpenRouter reasoning override.",
    )
    parser.add_argument("--max-units-per-call", type=int, default=1)
    parser.add_argument("--hydration-timeout-seconds", type=float, default=120.0)
    parser.add_argument("--verification-timeout-seconds", type=float, default=120.0)
    parser.add_argument("--support-timeout-seconds", type=float, default=30.0)
    parser.add_argument("--semantic-timeout-seconds", type=float, default=120.0)
    parser.add_argument("--budget-only", action="store_true", help="Stop after a no-cost selector payload.")
    parser.add_argument("--selector-budget-only", action="store_true", help="Stop after selector budget output.")
    parser.add_argument("--generation-budget-only", action="store_true", help="Run generation payloads without a model call.")
    parser.add_argument("--skip-hydration", action="store_true")
    parser.add_argument("--skip-generation", action="store_true")
    parser.add_argument("--skip-verification", action="store_true")
    parser.add_argument("--skip-gold-comparison", action="store_true")
    parser.add_argument("--semantic-coverage", action="store_true")
    parser.add_argument("--run-semantic-uncompiled", action="store_true")
    parser.add_argument("--materialize-visible-support", action="store_true")
    args = parser.parse_args()
    print(json.dumps(run(args), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
