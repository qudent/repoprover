"""Tests for the theorem-level LaTeX statement panel runner."""

import argparse
import json
from pathlib import Path

import pytest

from scripts.run_latex_statement_panel import load_panel_unit_ids, run


def _write_panel(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "unit_ids": [
                    "Book/Foo.tex:thm.one",
                    "Book/Bar.tex:prop.two",
                ]
            }
        ),
        encoding="utf-8",
    )


def _base_args(tmp_path: Path, **overrides: object) -> argparse.Namespace:
    panel = tmp_path / "panel.json"
    _write_panel(panel)
    values = {
        "panel": panel,
        "output": tmp_path / "panel-run",
        "selector_run": None,
        "generation_run": None,
        "project_root": tmp_path / "project",
        "base_url": "https://openrouter.ai/api/v1",
        "selector_model": "deepseek/deepseek-v4-flash",
        "generation_model": "deepseek/deepseek-v4-flash",
        "selector_max_tokens": 123,
        "generation_max_tokens": 456,
        "selector_temperature": 0.0,
        "generation_temperature": 0.0,
        "selector_reasoning_effort": "none",
        "generation_reasoning_effort": "none",
        "max_units_per_call": 1,
        "hydration_timeout_seconds": 2.0,
        "verification_timeout_seconds": 3.0,
        "support_timeout_seconds": 4.0,
        "semantic_timeout_seconds": 5.0,
        "budget_only": False,
        "selector_budget_only": False,
        "generation_budget_only": False,
        "skip_hydration": False,
        "skip_generation": False,
        "skip_verification": False,
        "skip_gold_comparison": False,
        "semantic_coverage": False,
        "run_semantic_uncompiled": False,
        "materialize_visible_support": False,
    }
    values.update(overrides)
    return argparse.Namespace(**values)


def _success(stage: str, command: list[str]) -> dict[str, object]:
    return {
        "stage": stage,
        "command": " ".join(command),
        "exit_code": 0,
        "elapsed_seconds": 0.01,
        "stdout_log": None,
        "stderr_log": None,
        "stdout_tail": "",
        "stderr_tail": "",
    }


def test_load_panel_rejects_duplicate_unit_ids(tmp_path: Path) -> None:
    panel = tmp_path / "panel.json"
    panel.write_text(json.dumps({"unit_ids": ["a", "a"]}), encoding="utf-8")

    with pytest.raises(ValueError, match="duplicate panel unit ids"):
        load_panel_unit_ids(panel)


def test_panel_budget_only_runs_selector_and_stops(monkeypatch, tmp_path: Path) -> None:
    args = _base_args(tmp_path, budget_only=True)
    calls: list[tuple[str, list[str]]] = []

    def fake_run_command(stage: str, command: list[str], *, output_root: Path) -> dict[str, object]:
        calls.append((stage, command))
        selector_eval = args.output / "context-selection" / "eval"
        selector_eval.mkdir(parents=True)
        (selector_eval / "context-selection-results.json").write_text(
            json.dumps(
                {
                    "budget_only": True,
                    "paid_call_made": False,
                    "valid_json": False,
                    "units_selected": 2,
                }
            ),
            encoding="utf-8",
        )
        return _success(stage, command)

    monkeypatch.setattr("scripts.run_latex_statement_panel.run_command", fake_run_command)

    summary = run(args)

    assert summary["stop_reason"] == "budget_only_after_context_selection"
    assert [stage for stage, _ in calls] == ["context_selection"]
    selector_command = calls[0][1]
    assert "--budget-only" in selector_command
    assert selector_command.count("--unit-id") == 2
    assert "--reasoning-effort" in selector_command
    assert "none" in selector_command
    written = json.loads((args.output / "eval" / "panel-summary.json").read_text(encoding="utf-8"))
    assert written["metrics"]["context_selection"]["units_selected"] == 2


def test_panel_full_flow_writes_summary(monkeypatch, tmp_path: Path) -> None:
    args = _base_args(tmp_path, semantic_coverage=True, materialize_visible_support=True)
    calls: list[str] = []

    def output_arg(command: list[str]) -> Path:
        return Path(command[command.index("--output") + 1])

    def fake_run_command(stage: str, command: list[str], *, output_root: Path) -> dict[str, object]:
        calls.append(stage)
        if stage == "context_selection":
            selector_eval = args.output / "context-selection" / "eval"
            selector_eval.mkdir(parents=True)
            (selector_eval / "context-selection-results.json").write_text(
                json.dumps(
                    {
                        "budget_only": False,
                        "paid_call_made": True,
                        "valid_json": True,
                        "units_selected": 2,
                        "elapsed_seconds": 1.2,
                        "cost_summary": {
                            "openrouter_reported_cost": 0.01,
                            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
                        },
                    }
                ),
                encoding="utf-8",
            )
        elif stage == "hydration":
            selector_eval = args.output / "context-selection" / "eval"
            (selector_eval / "mathlib-hydration-summary.json").write_text(
                json.dumps(
                    {
                        "batches": [
                            {
                                "request_count": 3,
                                "exact_identifier_count": 2,
                                "fallback_exact_identifier_count": 1,
                                "lean_check_status": "lean_errors",
                                "fallback_lean_check_status": "ok",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
        elif stage == "generation":
            generation_eval = args.output / "generation" / "eval"
            generation_eval.mkdir(parents=True)
            (generation_eval / "generation-results.json").write_text(
                json.dumps(
                    {
                        "budget_only": False,
                        "paid_call_made": True,
                        "valid_json": True,
                        "batch_count": 2,
                        "elapsed_seconds": 2.0,
                        "cost_summary": {
                            "openrouter_reported_cost": 0.02,
                            "batches": [
                                {
                                    "usage": {
                                        "prompt_tokens": 20,
                                        "completion_tokens": 8,
                                        "completion_tokens_details": {"reasoning_tokens": 0},
                                        "prompt_tokens_details": {"cached_tokens": 3},
                                    }
                                },
                                {
                                    "usage": {
                                        "prompt_tokens": 7,
                                        "completion_tokens": 2,
                                        "completion_tokens_details": {"reasoning_tokens": 1},
                                        "prompt_tokens_details": {"cached_tokens": 4},
                                    }
                                },
                            ],
                        },
                        "batches": [{"contract_enforcement": {"normalized_unit_count": 1}}],
                    }
                ),
                encoding="utf-8",
            )
        elif stage == "verification":
            path = output_arg(command)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(
                    {
                        "unit_count": 2,
                        "compile_passed_units": 1,
                        "failure_class_counts": {"declined_cannot_prove": 1},
                        "materialize_visible_support": True,
                    }
                ),
                encoding="utf-8",
            )
            assert "--materialize-visible-support" in command
        elif stage == "gold_comparison":
            path = output_arg(command)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(
                    {
                        "unit_count": 2,
                        "compile_passed_units": 1,
                        "compiled_name_overlap_units": 0,
                        "compiled_needs_semantic_review_units": 1,
                        "coverage_status_counts": {"compiled_needs_semantic_review": 1},
                    }
                ),
                encoding="utf-8",
            )
        elif stage == "semantic_coverage":
            path = output_arg(command)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(
                    {
                        "unit_count": 2,
                        "all_aligned_gold_proved_units": 1,
                        "coverage_status_counts": {"all_aligned_gold_proved": 1},
                    }
                ),
                encoding="utf-8",
            )
        return _success(stage, command)

    monkeypatch.setattr("scripts.run_latex_statement_panel.run_command", fake_run_command)

    summary = run(args)

    assert summary["stop_reason"] == "completed"
    assert calls == [
        "context_selection",
        "hydration",
        "generation",
        "verification",
        "gold_comparison",
        "semantic_coverage",
    ]
    metrics = summary["metrics"]
    assert metrics["context_selection"]["cost"] == 0.01
    assert metrics["hydration"]["request_count"] == 3
    assert metrics["generation"]["normalized_unit_count"] == 1
    assert metrics["generation"]["prompt_tokens"] == 27
    assert metrics["generation"]["completion_tokens"] == 10
    assert metrics["generation"]["cached_prompt_tokens"] == 7
    assert metrics["verification"]["compile_passed_units"] == 1
    assert metrics["gold_comparison"]["compiled_needs_semantic_review_units"] == 1
    assert metrics["semantic_coverage"]["all_aligned_gold_proved_units"] == 1
    assert (args.output / "eval" / "panel-summary.md").exists()


def test_panel_can_reuse_existing_generation_run(monkeypatch, tmp_path: Path) -> None:
    selector = tmp_path / "selector"
    selector_eval = selector / "eval"
    selector_eval.mkdir(parents=True)
    (selector_eval / "context-selection-results.json").write_text(
        json.dumps({"valid_json": True, "paid_call_made": True, "units_selected": 2}),
        encoding="utf-8",
    )
    generation = tmp_path / "existing-generation"
    generation_eval = generation / "eval"
    generation_eval.mkdir(parents=True)
    (generation_eval / "generation-results.json").write_text(
        json.dumps({"valid_json": True, "paid_call_made": True, "batch_count": 2, "batches": []}),
        encoding="utf-8",
    )
    args = _base_args(
        tmp_path,
        selector_run=selector,
        generation_run=generation,
        skip_hydration=True,
        skip_generation=True,
        materialize_visible_support=True,
    )
    calls: list[str] = []

    def output_arg(command: list[str]) -> Path:
        return Path(command[command.index("--output") + 1])

    def fake_run_command(stage: str, command: list[str], *, output_root: Path) -> dict[str, object]:
        calls.append(stage)
        path = output_arg(command)
        path.parent.mkdir(parents=True, exist_ok=True)
        if stage == "verification":
            assert "--materialize-visible-support" in command
            path.write_text(
                json.dumps({"unit_count": 2, "compile_passed_units": 2, "failure_class_counts": {"compiled": 2}}),
                encoding="utf-8",
            )
        elif stage == "gold_comparison":
            path.write_text(json.dumps({"unit_count": 2, "compile_passed_units": 2}), encoding="utf-8")
        return _success(stage, command)

    monkeypatch.setattr("scripts.run_latex_statement_panel.run_command", fake_run_command)

    summary = run(args)

    assert summary["stop_reason"] == "completed"
    assert calls == ["verification", "gold_comparison"]
    assert [stage["stage"] for stage in summary["stages"]] == [
        "context_selection",
        "generation",
        "verification",
        "gold_comparison",
    ]
    assert summary["stages"][1]["command"] == "reuse existing generation run"
    assert summary["metrics"]["generation"]["path"] == str(generation)
    assert summary["metrics"]["verification"]["compile_passed_units"] == 2
