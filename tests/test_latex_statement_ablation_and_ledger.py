"""Tests for theorem-level ablation commands and run ledger rows."""

import json
from pathlib import Path

from scripts.build_latex_statement_ablation_commands import build_rows
from scripts.update_latex_statement_run_ledger import update_ledger


def test_ablation_commands_preserve_fixed_selector_and_models() -> None:
    config = {
        "panels": {"fresh": "docs/fresh.json"},
        "fixed_selector_runs": {"fresh_selector": "docs/run/context-selection"},
        "proof_lane_task_dirs": {"fresh_tasks": "docs/tasks"},
        "defaults": {
            "output_root": "docs/ablation",
            "max_tokens": 123,
            "temperature": 0.0,
            "max_units_per_call": 1,
            "materialize_visible_support": True,
            "support_mode": "assumption",
            "semantic_coverage": True,
        },
        "runs": [
            {
                "id": "generation-pro",
                "kind": "panel_generation_fixed_selector",
                "panel": "fresh",
                "selector_run": "fresh_selector",
                "generation_model": "deepseek/deepseek-v4-pro",
                "generation_reasoning_effort": "none",
            },
            {
                "id": "proof-kimi",
                "kind": "proof_lane_generation",
                "proof_lane_task_dir": "fresh_tasks",
                "model": "moonshotai/kimi-k2.6",
                "reasoning_effort": "high",
                "max_tokens": 32768,
            },
        ],
    }

    rows = build_rows(config, "budget")

    generation = rows[0]["command"]
    assert "--selector-run" in generation
    assert "docs/run/context-selection" in generation
    assert "--generation-model" in generation
    assert "deepseek/deepseek-v4-pro" in generation
    assert "--generation-budget-only" in generation
    assert "--support-mode" in generation
    assert "assumption" in generation

    proof = rows[1]["command"]
    assert "--proof-lane-task-dir" in proof
    assert "docs/tasks" in proof
    assert "--model" in proof
    assert "moonshotai/kimi-k2.6" in proof
    assert "--reasoning-effort" in proof
    assert "high" in proof
    assert "--max-tokens" in proof
    assert "32768" in proof
    assert "--budget-only" in proof


def test_run_ledger_records_panel_generation_and_acceptance(tmp_path: Path) -> None:
    panel_root = tmp_path / "panel"
    (panel_root / "eval").mkdir(parents=True)
    (panel_root / "eval/panel-summary.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-05-06T00:00:00+00:00",
                "panel": "docs/panel.json",
                "unit_ids": ["u1", "u2"],
                "stop_reason": "completed",
                "stages": [
                    {
                        "stage": "context_selection",
                        "command": "python selector --model deepseek/deepseek-v4-flash --reasoning-effort none",
                    },
                    {
                        "stage": "generation",
                        "command": "python generation --model deepseek/deepseek-v4-pro --reasoning-effort none",
                    },
                ],
                "metrics": {
                    "context_selection": {
                        "cost": 0.01,
                        "prompt_tokens": 10,
                        "completion_tokens": 2,
                    },
                    "hydration": {
                        "lean_check_statuses": ["checked", "error"],
                        "fallback_lean_check_statuses": ["checked"],
                    },
                    "generation": {
                        "cost": 0.02,
                        "prompt_tokens": 20,
                        "completion_tokens": 4,
                        "reasoning_tokens": 1,
                    },
                    "verification": {
                        "compile_passed_units": 1,
                        "failure_class_counts": {"compile_failure": 1},
                    },
                    "semantic_coverage": {"all_aligned_gold_proved_units": 1},
                },
            }
        ),
        encoding="utf-8",
    )

    proof_root = tmp_path / "proof"
    (proof_root / "eval").mkdir(parents=True)
    (proof_root / "eval/generation-results.json").write_text(
        json.dumps(
            {
                "schema_version": "repoprover.latex_statement_proof_lane_generation.v1",
                "generated_at": "2026-05-06T00:01:00+00:00",
                "task_unit_keys": ["u2"],
                "model": "moonshotai/kimi-k2.6",
                "reasoning_effort": "none",
                "paid_call_made": True,
                "provider_error_count": 0,
                "cost_summary": {
                    "openrouter_reported_cost": 0.03,
                    "usage": {
                        "prompt_tokens": 30,
                        "completion_tokens": 6,
                        "completion_tokens_details": {"reasoning_tokens": 0},
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    (proof_root / "eval/verification-results-360s.json").write_text(
        json.dumps(
            {
                "compile_passed_units": 1,
                "failure_class_counts": {"compiled": 1},
                "lean_call_count": 7,
                "lean_elapsed_seconds": 12.5,
            }
        ),
        encoding="utf-8",
    )
    (proof_root / "eval/semantic-coverage-360s.json").write_text(
        json.dumps(
            {
                "all_aligned_gold_proved_units": 1,
                "coverage_status_counts": {"all_aligned_gold_proved": 1},
            }
        ),
        encoding="utf-8",
    )
    (proof_root / "eval/retry-cost-audit.json").write_text(
        json.dumps(
            {
                "manual_cost_adjustments": [
                    {
                        "openrouter_reported_cost": 0.04,
                        "prompt_tokens": 40,
                        "completion_tokens": 8,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    acceptance_root = tmp_path / "acceptance"
    (acceptance_root / "eval").mkdir(parents=True)
    (acceptance_root / "eval/proof-lane-acceptance-summary.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-05-06T00:02:00+00:00",
                "solution_unit_keys": ["u2"],
                "solution_generation_runs": [str(proof_root)],
                "verification": {
                    "compile_passed_units": 0,
                    "failure_class_counts": {"compile_failure": 1},
                },
                "semantic_coverage": {"all_aligned_gold_proved_units": 0},
                "task_leakage_scan": {"matches": []},
            }
        ),
        encoding="utf-8",
    )

    ledger = tmp_path / "ledger.jsonl"
    rows = update_ledger(ledger, [panel_root, proof_root, acceptance_root], notes="test")

    assert [row["run_type"] for row in rows] == ["panel", "proof_lane_generation", "proof_lane_acceptance"]
    assert rows[0]["cost"] == 0.03
    assert rows[0]["tokens"]["prompt_tokens"] == 30
    assert rows[0]["checked_context_count"] == 2
    assert rows[0]["failed_context_count"] == 1
    assert rows[1]["models"]["model"] == "moonshotai/kimi-k2.6"
    assert rows[1]["cost"] == 0.07
    assert rows[1]["tokens"]["prompt_tokens"] == 70
    assert rows[1]["compile_passed_units"] == 1
    assert rows[1]["failure_class_counts"] == {"compiled": 1}
    assert rows[1]["verification_lean_call_count"] == 7
    assert rows[1]["verification_lean_elapsed_seconds"] == 12.5
    assert rows[1]["verification_artifact"].endswith("verification-results-360s.json")
    assert rows[1]["semantic_passed_units"] == 1
    assert rows[1]["semantic_artifact"].endswith("semantic-coverage-360s.json")
    assert len(rows[1]["manual_cost_adjustments"]) == 1
    assert rows[2]["cost"] == 0.07
    assert rows[2]["leakage_match_count"] == 0
    assert len(ledger.read_text(encoding="utf-8").splitlines()) == 3

    update_ledger(ledger, [panel_root], notes="replacement")
    assert len(ledger.read_text(encoding="utf-8").splitlines()) == 3
