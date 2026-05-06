"""Tests for proof-lane acceptance orchestration."""

import argparse
import json
from pathlib import Path

import scripts.run_latex_statement_proof_lane_acceptance as acceptance


def _write_solution(path: Path, unit_key: str = "unit-002") -> None:
    path.write_text(
        json.dumps(
            {
                "units": [
                    {
                        "unit_key": unit_key,
                        "status": "generated",
                        "lean_file_body": "theorem proof_lane_solution : True := by trivial",
                        "declaration_names": ["proof_lane_solution"],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )


def _args(tmp_path: Path, task_dir: Path, solution: Path) -> argparse.Namespace:
    return argparse.Namespace(
        base_generation_run=tmp_path / "base",
        proof_lane_task_dir=task_dir,
        solution_generation_run=[solution],
        output=tmp_path / "accepted",
        selector_run=None,
        project_root=tmp_path / "project",
        imports=["Mathlib"],
        opens=[],
        infer_context=True,
        filter_target_module_imports=True,
        validate_inferred_opens=True,
        timeout_seconds=1.0,
        open_timeout_seconds=1.0,
        materialize_visible_support=True,
        support_timeout_seconds=1.0,
        semantic_coverage=True,
        allow_task_leakage=False,
    )


def test_acceptance_rejects_solution_unit_not_in_task_set(tmp_path: Path) -> None:
    task_dir = tmp_path / "tasks"
    task_dir.mkdir()
    (task_dir / "proof-lane-summary.json").write_text(
        json.dumps({"unit_keys": ["unit-001"]}),
        encoding="utf-8",
    )
    solution = tmp_path / "solution.json"
    _write_solution(solution, unit_key="unit-002")

    try:
        acceptance.run(_args(tmp_path, task_dir, solution))
    except ValueError as exc:
        assert "not present in target-hidden task set" in str(exc)
    else:
        raise AssertionError("expected proof-lane acceptance to reject unexpected unit key")


def test_acceptance_runs_merge_verify_and_graders(monkeypatch, tmp_path: Path) -> None:
    task_dir = tmp_path / "tasks"
    task_dir.mkdir()
    (task_dir / "proof-lane-summary.json").write_text(
        json.dumps({"unit_keys": ["unit-002"]}),
        encoding="utf-8",
    )
    solution = tmp_path / "solution.json"
    _write_solution(solution)
    calls: list[str] = []

    def fake_merge(args: argparse.Namespace) -> dict:
        calls.append("merge")
        (args.output / "eval").mkdir(parents=True, exist_ok=True)
        return {"selector_run": "selector/run"}

    def fake_verify(args: argparse.Namespace) -> dict:
        calls.append("verify")
        summary = {
            "compile_passed_units": 1,
            "unit_count": 1,
            "failure_class_counts": {"compiled": 1},
            "batches": [
                {
                    "units": [
                        {
                            "unit_key": "unit-002",
                            "compile_passed": True,
                            "failure_class": "compiled",
                            "reported_status": "generated",
                        }
                    ]
                }
            ],
        }
        acceptance.write_json(args.output, summary)
        return summary

    def fake_exact(selector_run: Path, generation_run: Path, *, verification_path: Path | None = None) -> dict:
        calls.append("exact")
        assert str(selector_run) == "selector/run"
        assert verification_path == tmp_path / "accepted/eval/verification-results.json"
        return {
            "coverage_status_counts": {"compiled_needs_semantic_review": 1},
            "compiled_name_overlap_units": 0,
            "compiled_needs_semantic_review_units": 1,
        }

    def fake_semantic(args: argparse.Namespace) -> dict:
        calls.append("semantic")
        return {
            "all_aligned_gold_proved_units": 1,
            "unit_count": 1,
            "coverage_status_counts": {"all_aligned_gold_proved": 1},
            "units": [
                {
                    "unit_key": "unit-002",
                    "coverage_status": "all_aligned_gold_proved",
                    "semantic_passed_gold_declarations": 1,
                    "aligned_gold_declaration_count": 1,
                }
            ],
        }

    monkeypatch.setattr(acceptance, "merge_run", fake_merge)
    monkeypatch.setattr(acceptance, "verify_run", fake_verify)
    monkeypatch.setattr(acceptance, "exact_compare", fake_exact)
    monkeypatch.setattr(acceptance, "semantic_compare", fake_semantic)

    summary = acceptance.run(_args(tmp_path, task_dir, solution))

    assert calls == ["merge", "verify", "exact", "semantic"]
    assert summary["no_paid_call_made"] is True
    assert summary["solution_unit_keys"] == ["unit-002"]
    assert summary["solution_failure_class_counts"] == {"compiled": 1}
    assert summary["solution_semantic_status_counts"] == {"all_aligned_gold_proved": 1}
    assert (tmp_path / "accepted/eval/proof-lane-acceptance-summary.md").exists()
