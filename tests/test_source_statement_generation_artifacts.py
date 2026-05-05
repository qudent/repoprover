"""Tests for archived source-statement generation artifact consumers."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.repair_source_statement_generation import run as run_repair_queue
from scripts.verify_source_statement_generation import load_tasks


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def _fake_response(body: str, *, cost: float = 0.001) -> dict:
    return {
        "model": "deepseek/deepseek-v4-pro",
        "choices": [{"message": {"content": body}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30, "cost": cost},
    }


def _write_archived_run(tmp_path: Path) -> Path:
    run_output = tmp_path / "run"
    _write_jsonl(
        run_output / "eval/selected-records.jsonl",
        [
            {"id": "Demo.lean:Demo.bad"},
            {"id": "Demo.lean:Demo.good"},
        ],
    )
    _write_json(
        run_output / "eval/verification-results.json",
        {
            "results": [
                {
                    "index": 1,
                    "record_id": "Demo.lean:Demo.bad",
                    "failure_class": "generated_lean_does_not_compile",
                },
                {
                    "index": 2,
                    "record_id": "Demo.lean:Demo.good",
                    "failure_class": "grader_gold_statement_not_proved",
                },
            ]
        },
    )
    original_user = {"context": {"lean_prefix_context": "namespace Demo"}, "instructions": []}
    _write_json(
        run_output / "record-001/openrouter-payload.json",
        {"messages": [{"role": "system", "content": "system"}, {"role": "user", "content": json.dumps(original_user)}]},
    )
    _write_json(
        run_output / "record-001/model-output.json",
        {
            "lean_declaration": "theorem bad : True := by\n  exact missingFact",
            "declaration_name": "bad",
        },
    )
    _write_json(
        run_output / "record-001/verification-generated-only-lean.json",
        {"exit_code": 1, "output": "unknown identifier 'missingFact'"},
    )
    return run_output


def _repair_args(run_output: Path, **overrides) -> argparse.Namespace:
    values = {
        "run_output": run_output,
        "verification_results": "verification-results.json",
        "failed_model_output_name": "model-output.json",
        "generated_only_lean_name": "verification-generated-only-lean.json",
        "attempt": 1,
        "model": "deepseek/deepseek-v4-pro",
        "base_url": "https://openrouter.ai/api/v1",
        "max_tokens": 128,
        "temperature": 0.0,
        "reasoning_effort": "high",
        "openrouter_timeout": 30.0,
        "max_actual_cost_usd": 0.25,
        "concurrency": 2,
        "budget_only": False,
        "include_non_compile_failures": False,
    }
    values.update(overrides)
    return argparse.Namespace(**values)


def test_repair_queue_targets_compile_failures_and_writes_payload(tmp_path: Path) -> None:
    run_output = _write_archived_run(tmp_path)

    summary = run_repair_queue(_repair_args(run_output, budget_only=True))

    assert summary["records_completed"] == 1
    assert summary["paid_calls_made"] == 0
    payload = json.loads((run_output / "record-001/repair-attempt-001-openrouter-payload.json").read_text(encoding="utf-8"))
    user = json.loads(payload["messages"][1]["content"])
    assert "theorem bad : True" in user["failed_generated_declaration"]
    assert "unknown identifier 'missingFact'" in user["generated_only_lean_output"]
    assert not (run_output / "record-002/repair-attempt-001-openrouter-payload.json").exists()


def test_repair_queue_writes_repair_model_artifacts(tmp_path: Path, monkeypatch) -> None:
    run_output = _write_archived_run(tmp_path)

    def fake_call_openrouter(payload: dict, base_url: str, timeout: float) -> dict:
        body = json.dumps(
            {
                "lean_declaration": "theorem repaired : True := by\n  trivial",
                "declaration_name": "repaired",
                "used_context": ["compiler error"],
                "notes": [],
            }
        )
        return _fake_response(body, cost=0.0002)

    monkeypatch.setattr("scripts.repair_source_statement_generation.call_openrouter", fake_call_openrouter)

    summary = run_repair_queue(_repair_args(run_output))

    assert summary["paid_calls_made"] == 1
    assert summary["actual_cost_usd"] == 0.0002
    assert summary["repair_generation_successes"] == 1
    assert (run_output / "record-001/repair-attempt-001-model-output.json").exists()
    assert (run_output / "record-001/repair-attempt-001-lean-declaration.lean").read_text(encoding="utf-8") == (
        "theorem repaired : True := by\n  trivial\n"
    )


def test_verifier_can_load_repair_model_outputs(tmp_path: Path) -> None:
    run_output = _write_archived_run(tmp_path)
    _write_json(
        run_output / "record-001/repair-attempt-001-model-output.json",
        {
            "lean_declaration": "theorem repaired : True := by\n  trivial",
            "declaration_name": "repaired",
        },
    )

    tasks = load_tasks(run_output, model_output_name="repair-attempt-001-model-output.json")

    assert tasks[0]["model_output_path"].endswith("repair-attempt-001-model-output.json")
    assert tasks[1]["failure_class"] == "missing_model_output"
