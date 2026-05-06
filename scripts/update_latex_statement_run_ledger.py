#!/usr/bin/env python3
"""Append compact theorem-level run summaries to a JSONL ledger."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_LEDGER = Path("docs/latex-statement-run-ledger.jsonl")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")


def usage_totals_from_cost_summary(cost_summary: dict[str, Any] | None) -> dict[str, int]:
    totals = {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "reasoning_tokens": 0,
        "cached_prompt_tokens": 0,
    }
    if not cost_summary:
        return totals

    def add_usage(usage: dict[str, Any]) -> None:
        details = usage.get("completion_tokens_details") or {}
        prompt_details = usage.get("prompt_tokens_details") or {}
        totals["prompt_tokens"] += int(usage.get("prompt_tokens") or 0)
        totals["completion_tokens"] += int(usage.get("completion_tokens") or 0)
        totals["reasoning_tokens"] += int(details.get("reasoning_tokens") or 0)
        totals["cached_prompt_tokens"] += int(prompt_details.get("cached_tokens") or 0)

    if isinstance(cost_summary.get("usage"), dict):
        add_usage(cost_summary["usage"])
    for batch in cost_summary.get("batches") or []:
        usage = (batch or {}).get("usage")
        if isinstance(usage, dict):
            add_usage(usage)
    for archived in cost_summary.get("archived_attempts") or []:
        usage = (archived or {}).get("usage")
        if isinstance(usage, dict):
            add_usage(usage)
    return totals


def cost_value(summary: dict[str, Any] | None) -> float:
    if not summary:
        return 0.0
    cost_summary = summary.get("cost_summary") or {}
    value = cost_summary.get("openrouter_reported_cost")
    if value is None:
        usage = cost_summary.get("usage") or {}
        value = usage.get("cost")
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


def option_after(command: str, option: str) -> str | None:
    parts = command.split()
    for index, part in enumerate(parts):
        if part == option and index + 1 < len(parts):
            return parts[index + 1]
    return None


def model_info_from_panel(summary: dict[str, Any]) -> dict[str, Any]:
    info: dict[str, Any] = {}
    for stage in summary.get("stages") or []:
        command = str(stage.get("command") or "")
        if stage.get("stage") == "context_selection":
            info["selector_model"] = option_after(command, "--model") or option_after(command, "--selector-model")
            info["selector_reasoning_effort"] = option_after(command, "--reasoning-effort")
        if stage.get("stage") == "generation":
            info["generation_model"] = option_after(command, "--model") or option_after(command, "--generation-model")
            info["generation_reasoning_effort"] = option_after(command, "--reasoning-effort")
    return {key: value for key, value in info.items() if value}


def hydration_counts(hydration: dict[str, Any] | None) -> dict[str, int]:
    if not hydration:
        return {"checked_context_count": 0, "failed_context_count": 0}
    checked = 0
    failed = 0
    for status in hydration.get("lean_check_statuses") or []:
        if status == "checked":
            checked += 1
        elif status:
            failed += 1
    for status in hydration.get("fallback_lean_check_statuses") or []:
        if status == "checked":
            checked += 1
        elif status:
            failed += 1
    return {"checked_context_count": checked, "failed_context_count": failed}


def row_from_panel(root: Path) -> dict[str, Any]:
    summary = read_json(root / "eval" / "panel-summary.json")
    metrics = summary.get("metrics") or {}
    context = metrics.get("context_selection") or {}
    generation = metrics.get("generation") or {}
    verification = metrics.get("verification") or {}
    semantic = metrics.get("semantic_coverage") or {}
    cost = float(context.get("cost") or 0.0) + float(generation.get("cost") or 0.0)
    tokens = {
        "prompt_tokens": int(context.get("prompt_tokens") or 0) + int(generation.get("prompt_tokens") or 0),
        "completion_tokens": int(context.get("completion_tokens") or 0) + int(generation.get("completion_tokens") or 0),
        "reasoning_tokens": int(context.get("reasoning_tokens") or 0) + int(generation.get("reasoning_tokens") or 0),
        "cached_prompt_tokens": int(context.get("cached_prompt_tokens") or 0)
        + int(generation.get("cached_prompt_tokens") or 0),
    }
    return {
        "schema_version": "repoprover.latex_statement_run_ledger_row.v1",
        "artifact_root": str(root),
        "run_type": "panel",
        "generated_at": summary.get("generated_at"),
        "panel": summary.get("panel"),
        "unit_ids": summary.get("unit_ids") or [],
        "stop_reason": summary.get("stop_reason"),
        "models": model_info_from_panel(summary),
        "cost": cost,
        "tokens": tokens,
        **hydration_counts(metrics.get("hydration")),
        "compile_passed_units": verification.get("compile_passed_units"),
        "semantic_passed_units": semantic.get("all_aligned_gold_proved_units"),
        "failure_class_counts": verification.get("failure_class_counts") or {},
    }


def row_from_generation(root: Path) -> dict[str, Any]:
    summary = read_json(root / "eval" / "generation-results.json")
    cost_adjustment = retry_cost_adjustment(root)
    row = {
        "schema_version": "repoprover.latex_statement_run_ledger_row.v1",
        "artifact_root": str(root),
        "run_type": "proof_lane_generation"
        if "proof_lane" in str(summary.get("schema_version") or "")
        else "generation",
        "generated_at": summary.get("generated_at"),
        "unit_ids": summary.get("task_unit_keys") or summary.get("unit_keys") or [],
        "models": {
            "model": summary.get("model"),
            "reasoning_effort": summary.get("reasoning_effort"),
        },
        "cost": cost_value(summary) + cost_adjustment["cost"],
        "tokens": add_token_totals(
            usage_totals_from_cost_summary(summary.get("cost_summary") or {}),
            cost_adjustment["tokens"],
        ),
        "provider_error_count": summary.get("provider_error_count"),
        "paid_call_made": summary.get("paid_call_made"),
    }
    if verification := latest_verification_summary(root):
        verification_path, verification_summary = verification
        row.update(
            {
                "verification_artifact": str(verification_path),
                "compile_passed_units": verification_summary.get("compile_passed_units"),
                "failure_class_counts": verification_summary.get("failure_class_counts") or {},
                "verification_lean_call_count": verification_summary.get("lean_call_count"),
                "verification_lean_elapsed_seconds": verification_summary.get("lean_elapsed_seconds"),
            }
        )
    if semantic := latest_semantic_summary(root):
        semantic_path, semantic_summary = semantic
        row.update(
            {
                "semantic_artifact": str(semantic_path),
                "semantic_passed_units": semantic_summary.get("all_aligned_gold_proved_units"),
                "semantic_status_counts": semantic_summary.get("coverage_status_counts") or {},
            }
        )
    if cost_adjustment["entries"]:
        row["manual_cost_adjustments"] = cost_adjustment["entries"]
    return row


def latest_verification_summary(root: Path) -> tuple[Path, dict[str, Any]] | None:
    candidates = sorted((root / "eval").glob("verification-results*.json"), key=lambda path: path.stat().st_mtime)
    if not candidates:
        return None
    path = candidates[-1]
    return path, read_json(path)


def latest_semantic_summary(root: Path) -> tuple[Path, dict[str, Any]] | None:
    candidates = sorted((root / "eval").glob("semantic-coverage*.json"), key=lambda path: path.stat().st_mtime)
    if not candidates:
        return None
    path = candidates[-1]
    return path, read_json(path)


def add_token_totals(left: dict[str, int], right: dict[str, int]) -> dict[str, int]:
    merged = dict(left)
    for key, value in right.items():
        merged[key] = int(merged.get(key) or 0) + int(value or 0)
    return merged


def retry_cost_adjustment(root: Path) -> dict[str, Any]:
    path = root / "eval" / "retry-cost-audit.json"
    if not path.exists():
        return {
            "cost": 0.0,
            "tokens": {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "reasoning_tokens": 0,
                "cached_prompt_tokens": 0,
            },
            "entries": [],
        }
    data = read_json(path)
    entries = data.get("manual_cost_adjustments") or []
    total_cost = 0.0
    totals = {"prompt_tokens": 0, "completion_tokens": 0, "reasoning_tokens": 0, "cached_prompt_tokens": 0}
    for entry in entries:
        try:
            total_cost += float(entry.get("openrouter_reported_cost") or 0.0)
        except (TypeError, ValueError):
            pass
        for key in totals:
            totals[key] += int(entry.get(key) or 0)
    return {"cost": total_cost, "tokens": totals, "entries": entries}


def row_from_acceptance(root: Path) -> dict[str, Any]:
    summary = read_json(root / "eval" / "proof-lane-acceptance-summary.json")
    verification = summary.get("verification") or {}
    semantic = summary.get("semantic_coverage") or {}
    solution_cost = 0.0
    solution_tokens = {"prompt_tokens": 0, "completion_tokens": 0, "reasoning_tokens": 0, "cached_prompt_tokens": 0}
    for run_path in summary.get("solution_generation_runs") or []:
        generation_root = Path(run_path)
        gen_path = generation_root / "eval" / "generation-results.json"
        if not gen_path.exists():
            continue
        generation = read_json(gen_path)
        solution_cost += cost_value(generation)
        usage = usage_totals_from_cost_summary(generation.get("cost_summary") or {})
        for key, value in usage.items():
            solution_tokens[key] += value
        adjustment = retry_cost_adjustment(generation_root)
        solution_cost += adjustment["cost"]
        for key, value in adjustment["tokens"].items():
            solution_tokens[key] += value
    return {
        "schema_version": "repoprover.latex_statement_run_ledger_row.v1",
        "artifact_root": str(root),
        "run_type": "proof_lane_acceptance",
        "generated_at": summary.get("generated_at"),
        "unit_ids": summary.get("solution_unit_keys") or [],
        "stop_reason": "completed",
        "cost": solution_cost,
        "tokens": solution_tokens,
        "compile_passed_units": verification.get("compile_passed_units"),
        "semantic_passed_units": semantic.get("all_aligned_gold_proved_units"),
        "failure_class_counts": verification.get("failure_class_counts") or {},
        "leakage_match_count": len((summary.get("task_leakage_scan") or {}).get("matches") or []),
    }


def row_from_artifact_root(root: Path) -> dict[str, Any]:
    if (root / "eval" / "panel-summary.json").exists():
        return row_from_panel(root)
    if (root / "eval" / "proof-lane-acceptance-summary.json").exists():
        return row_from_acceptance(root)
    if (root / "eval" / "generation-results.json").exists():
        return row_from_generation(root)
    raise ValueError(f"{root}: no supported eval summary found")


def update_ledger(ledger: Path, artifact_roots: list[Path], notes: str | None = None) -> list[dict[str, Any]]:
    existing = read_jsonl(ledger)
    new_rows = []
    recorded_at = datetime.now(timezone.utc).isoformat()
    for root in artifact_roots:
        row = row_from_artifact_root(root)
        row["recorded_at"] = recorded_at
        if notes:
            row["notes"] = notes
        new_rows.append(row)
    replace_roots = {row["artifact_root"] for row in new_rows}
    rows = [row for row in existing if row.get("artifact_root") not in replace_roots]
    rows.extend(new_rows)
    write_jsonl(ledger, rows)
    return new_rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument("--artifact-root", type=Path, action="append", required=True)
    parser.add_argument("--notes")
    args = parser.parse_args()
    rows = update_ledger(args.ledger, args.artifact_root, notes=args.notes)
    print(json.dumps({"ledger": str(args.ledger), "rows_written": rows}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
