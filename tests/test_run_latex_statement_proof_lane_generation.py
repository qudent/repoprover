"""Tests for proof-lane generation prompt construction."""

import argparse
import json
from pathlib import Path

from scripts.run_latex_statement_proof_lane_generation import run


def _write_task(task_dir: Path, unit_key: str = "unit-002") -> None:
    tasks_dir = task_dir / "tasks"
    tasks_dir.mkdir(parents=True, exist_ok=True)
    (tasks_dir / f"{unit_key}.json").write_text(
        json.dumps(
            {
                "schema_version": "repoprover.latex_statement_proof_lane_task.v1",
                "unit_key": unit_key,
                "source_unit": {"source_text": "demo source"},
                "current_generation": {"status": "cannot_prove_from_visible_context"},
                "verification": {"failure_class": "declined_cannot_prove"},
                "visible_prompt_context": {
                    "planned_declarations": [
                        {
                            "task_id": f"{unit_key}-task-1",
                            "hydrated_mathlib_context": [
                                {
                                    "exact_identifier": "Nat.add_zero",
                                    "lean_check": {"status": "checked", "signature": "Nat.add_zero ..."},
                                }
                            ],
                        }
                    ]
                },
                "benchmark_policy": {"posthoc_alignment_hidden": True},
            }
        ),
        encoding="utf-8",
    )


def test_budget_only_writes_reviewable_payload(tmp_path: Path) -> None:
    task_dir = tmp_path / "proof-lane"
    _write_task(task_dir)
    output = tmp_path / "run"

    summary = run(
        argparse.Namespace(
            proof_lane_task_dir=task_dir,
            unit_key=None,
            output=output,
            model="model/id",
            base_url="https://example.invalid",
            max_tokens=1234,
            temperature=0.0,
            reasoning_effort="none",
            max_tasks_per_call=1,
            budget_only=True,
        )
    )

    payload = json.loads((output / "batch-001/generation-payload.json").read_text(encoding="utf-8"))
    user_payload = json.loads(payload["messages"][1]["content"])

    assert summary["paid_call_made"] is False
    assert summary["task_unit_keys"] == ["unit-002"]
    assert payload["model"] == "model/id"
    assert user_payload["proof_lane_tasks"][0]["unit_key"] == "unit-002"
    assert user_payload["benchmark_policy"]["target_lean_available_to_proof_lane_generator"] is False
    assert "Nat.add_zero" in json.dumps(user_payload, ensure_ascii=False)


def test_budget_only_filters_requested_unit_key(tmp_path: Path) -> None:
    task_dir = tmp_path / "proof-lane"
    _write_task(task_dir, unit_key="unit-001")
    _write_task(task_dir, unit_key="unit-002")
    output = tmp_path / "run"

    summary = run(
        argparse.Namespace(
            proof_lane_task_dir=task_dir,
            unit_key=["unit-002"],
            output=output,
            model="model/id",
            base_url="https://example.invalid",
            max_tokens=1234,
            temperature=0.0,
            reasoning_effort="none",
            max_tasks_per_call=1,
            budget_only=True,
        )
    )

    assert summary["task_unit_keys"] == ["unit-002"]
    assert summary["batch_count"] == 1
