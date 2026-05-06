"""Tests for the bounded theorem-level repair-loop runner."""

import argparse
from pathlib import Path

from scripts.run_latex_statement_repair_loop import (
    preserve_compile_clean_units,
    run,
    semantic_source_coverage_review_keys,
    semantic_success_keys,
)


def _base_args(tmp_path: Path) -> argparse.Namespace:
    initial_generation = tmp_path / "initial-generation"
    initial_verification = initial_generation / "eval" / "verification-results.json"
    initial_verification.parent.mkdir(parents=True)
    initial_verification.write_text('{"unit_count":1,"compile_passed_units":0}\n', encoding="utf-8")
    return argparse.Namespace(
        selector_run=tmp_path / "selector",
        initial_generation_run=initial_generation,
        initial_verification_results=initial_verification,
        initial_semantic_coverage_results=None,
        output_root=tmp_path / "loop",
        max_rounds=2,
        extra_context=None,
        model="deepseek/deepseek-v4-flash",
        base_url="https://openrouter.ai/api/v1",
        max_tokens=256,
        temperature=0.0,
        reasoning_effort="none",
        project_root=tmp_path,
        hydration_imports=["Mathlib"],
        hydration_opens=[],
        verification_imports=["Mathlib"],
        verification_opens=[],
        materialize_visible_support=False,
        timeout_seconds=1.0,
        semantic_coverage=False,
        budget_only=False,
    )


def test_repair_loop_budget_only_stops_after_context_selection(monkeypatch, tmp_path: Path) -> None:
    args = _base_args(tmp_path)
    args.budget_only = True
    calls: list[str] = []

    def fake_context_selection(namespace):
        calls.append("context")
        return {"budget_only": True, "output_path": str(namespace.output)}

    monkeypatch.setattr("scripts.run_latex_statement_repair_loop.run_context_selection", fake_context_selection)
    monkeypatch.setattr(
        "scripts.run_latex_statement_repair_loop.run_hydration",
        lambda namespace: calls.append("hydration"),
    )

    summary = run(args)

    assert summary["stop_reason"] == "budget_only_after_context_selection"
    assert calls == ["context"]
    assert (args.output_root / "repair-loop-summary.json").exists()


def test_repair_loop_runs_round_and_stops_on_compile(monkeypatch, tmp_path: Path) -> None:
    args = _base_args(tmp_path)
    args.semantic_coverage = True
    args.materialize_visible_support = True
    calls: list[str] = []
    repair_extra_contexts: list[list[Path]] = []
    verification_materialize_flags: list[bool] = []

    def fake_context_selection(namespace):
        calls.append("context")
        return {"valid_json": True, "output_path": str(namespace.output)}

    def fake_hydration(namespace):
        calls.append("hydration")
        return {"batches": [{"hydrated_path": str(namespace.run / "batch-001/mathlib-lean-hydrated-context.json")}]}

    def fake_pack(namespace):
        calls.append("pack")
        namespace.output.parent.mkdir(parents=True, exist_ok=True)
        namespace.output.write_text('{"checked_signatures":[]}\n', encoding="utf-8")
        return {"output": str(namespace.output), "checked_signature_count": 0}

    def fake_repair(namespace):
        calls.append("repair")
        repair_extra_contexts.append(list(namespace.extra_context))
        batch = namespace.output / "batch-001"
        batch.mkdir(parents=True, exist_ok=True)
        (batch / "generation-output.json").write_text('{"units":[]}\n', encoding="utf-8")
        return {"output_path": str(namespace.output), "valid_json": True}

    def fake_verify(namespace):
        calls.append("verify")
        verification_materialize_flags.append(namespace.materialize_visible_support)
        namespace.output.parent.mkdir(parents=True, exist_ok=True)
        namespace.output.write_text('{"unit_count":1,"compile_passed_units":1}\n', encoding="utf-8")
        return {"unit_count": 1, "compile_passed_units": 1}

    def fake_gold(selector_run, generation_run, *, verification_path=None):
        calls.append("gold")
        return {"unit_count": 1}

    def fake_semantic(namespace):
        calls.append("semantic")
        return {"unit_count": 1, "all_aligned_gold_proved_units": 1}

    monkeypatch.setattr("scripts.run_latex_statement_repair_loop.run_context_selection", fake_context_selection)
    monkeypatch.setattr("scripts.run_latex_statement_repair_loop.run_hydration", fake_hydration)
    monkeypatch.setattr("scripts.run_latex_statement_repair_loop.run_context_pack", fake_pack)
    monkeypatch.setattr("scripts.run_latex_statement_repair_loop.run_repair", fake_repair)
    monkeypatch.setattr("scripts.run_latex_statement_repair_loop.run_verification", fake_verify)
    monkeypatch.setattr("scripts.run_latex_statement_repair_loop.compare_to_gold", fake_gold)
    monkeypatch.setattr("scripts.run_latex_statement_repair_loop.semantic_compare", fake_semantic)

    summary = run(args)

    assert summary["stop_reason"] == "all_units_semantically_covered"
    assert summary["materialize_visible_support"] is True
    assert summary["final_generation_run"] == str(args.output_root / "round-01-repair")
    assert calls == ["context", "hydration", "pack", "repair", "verify", "gold", "semantic"]
    assert repair_extra_contexts == [[args.output_root / "round-01-context" / "checked-repair-context.json"]]
    assert verification_materialize_flags == [True]


def test_preserve_compile_clean_units_replaces_repaired_output(tmp_path: Path) -> None:
    previous = tmp_path / "previous"
    repair = tmp_path / "repair"
    (previous / "batch-001").mkdir(parents=True)
    (previous / "eval").mkdir()
    (repair / "batch-001").mkdir(parents=True)
    previous_output = {
        "units": [
            {"unit_key": "unit-001", "status": "generated", "lean_file_body": "clean", "declaration_names": ["clean"]},
            {"unit_key": "unit-002", "status": "generated", "lean_file_body": "bad", "declaration_names": ["bad"]},
        ]
    }
    repaired_output = {
        "units": [
            {"unit_key": "unit-001", "status": "generated", "lean_file_body": "regressed", "declaration_names": ["regressed"]},
            {"unit_key": "unit-002", "status": "generated", "lean_file_body": "fixed", "declaration_names": ["fixed"]},
        ]
    }
    verification = {
        "batches": [
            {
                "units": [
                    {"unit_key": "unit-001", "compile_passed": True},
                    {"unit_key": "unit-002", "compile_passed": False},
                ]
            }
        ]
    }
    (previous / "batch-001/generation-output.json").write_text('{\n  "units": []\n}\n', encoding="utf-8")
    (previous / "batch-001/generation-output.json").write_text(__import__("json").dumps(previous_output), encoding="utf-8")
    (previous / "eval/verification-results.json").write_text(__import__("json").dumps(verification), encoding="utf-8")
    for name in ("generation-output.json", "repair-output.json"):
        (repair / "batch-001" / name).write_text(__import__("json").dumps(repaired_output), encoding="utf-8")

    summary = preserve_compile_clean_units(
        previous_generation_run=previous,
        previous_verification_results=previous / "eval/verification-results.json",
        repair_run=repair,
    )

    merged = __import__("json").loads((repair / "eval/merged-generation-output.json").read_text())
    first_batch = __import__("json").loads((repair / "batch-001/generation-output.json").read_text())
    second_batch = __import__("json").loads((repair / "batch-002/generation-output.json").read_text())
    assert summary["preserved_unit_keys"] == ["unit-001"]
    assert [unit["lean_file_body"] for unit in merged["units"]] == ["clean", "fixed"]
    assert [unit["unit_key"] for unit in first_batch["units"]] == ["unit-001"]
    assert [unit["unit_key"] for unit in second_batch["units"]] == ["unit-002"]


def test_preserve_compile_clean_units_aggregates_multibatch_previous_output(tmp_path: Path) -> None:
    previous = tmp_path / "previous"
    repair = tmp_path / "repair"
    (previous / "batch-001").mkdir(parents=True)
    (previous / "batch-002").mkdir(parents=True)
    (previous / "eval").mkdir()
    (repair / "batch-001").mkdir(parents=True)
    (previous / "batch-001/generation-output.json").write_text(
        __import__("json").dumps(
            {"units": [{"unit_key": "unit-001", "lean_file_body": "clean", "declaration_names": ["clean"]}]}
        ),
        encoding="utf-8",
    )
    (previous / "batch-002/generation-output.json").write_text(
        __import__("json").dumps(
            {"units": [{"unit_key": "unit-002", "lean_file_body": "bad", "declaration_names": ["bad"]}]}
        ),
        encoding="utf-8",
    )
    (previous / "batch-001/generation-payload.json").write_text(
        __import__("json").dumps({"marker": "payload-unit-001"}),
        encoding="utf-8",
    )
    (previous / "batch-002/generation-payload.json").write_text(
        __import__("json").dumps({"marker": "payload-unit-002"}),
        encoding="utf-8",
    )
    (previous / "eval/verification-results.json").write_text(
        __import__("json").dumps(
            {
                "batches": [
                    {"units": [{"unit_key": "unit-001", "compile_passed": True}]},
                    {"units": [{"unit_key": "unit-002", "compile_passed": False}]},
                ]
            }
        ),
        encoding="utf-8",
    )
    repaired_output = {
        "units": [{"unit_key": "unit-002", "lean_file_body": "fixed", "declaration_names": ["fixed"]}]
    }
    for name in ("generation-output.json", "repair-output.json"):
        (repair / "batch-001" / name).write_text(__import__("json").dumps(repaired_output), encoding="utf-8")

    summary = preserve_compile_clean_units(
        previous_generation_run=previous,
        previous_verification_results=previous / "eval/verification-results.json",
        repair_run=repair,
    )

    merged = __import__("json").loads((repair / "eval/merged-generation-output.json").read_text())
    first_batch = __import__("json").loads((repair / "batch-001/generation-output.json").read_text())
    second_batch = __import__("json").loads((repair / "batch-002/generation-output.json").read_text())
    first_payload = __import__("json").loads((repair / "batch-001/generation-payload.json").read_text())
    second_payload = __import__("json").loads((repair / "batch-002/generation-payload.json").read_text())
    assert summary["preserved_unit_keys"] == ["unit-001"]
    assert summary["carried_forward_unit_keys"] == []
    assert [unit["unit_key"] for unit in merged["units"]] == ["unit-001", "unit-002"]
    assert [unit["lean_file_body"] for unit in merged["units"]] == ["clean", "fixed"]
    assert [unit["unit_key"] for unit in first_batch["units"]] == ["unit-001"]
    assert [unit["unit_key"] for unit in second_batch["units"]] == ["unit-002"]
    assert first_payload["marker"] == "payload-unit-001"
    assert second_payload["marker"] == "payload-unit-002"
    assert [row["unit_key"] for row in summary["split_payload_sources"]] == ["unit-001", "unit-002"]


def test_preserve_compile_clean_units_can_use_semantic_success_keys(tmp_path: Path) -> None:
    previous = tmp_path / "previous"
    repair = tmp_path / "repair"
    (previous / "batch-001").mkdir(parents=True)
    (previous / "eval").mkdir()
    (repair / "batch-001").mkdir(parents=True)
    previous_output = {
        "units": [
            {"unit_key": "unit-001", "lean_file_body": "semantic-clean", "declaration_names": ["clean"]},
            {"unit_key": "unit-002", "lean_file_body": "compile-only", "declaration_names": ["partial"]},
        ]
    }
    repaired_output = {
        "units": [
            {"unit_key": "unit-001", "lean_file_body": "regressed", "declaration_names": ["regressed"]},
            {"unit_key": "unit-002", "lean_file_body": "semantic-fixed", "declaration_names": ["fixed"]},
        ]
    }
    verification = {
        "batches": [
            {
                "units": [
                    {"unit_key": "unit-001", "compile_passed": True},
                    {"unit_key": "unit-002", "compile_passed": True},
                ]
            }
        ]
    }
    (previous / "batch-001/generation-output.json").write_text(__import__("json").dumps(previous_output), encoding="utf-8")
    (previous / "eval/verification-results.json").write_text(__import__("json").dumps(verification), encoding="utf-8")
    for name in ("generation-output.json", "repair-output.json"):
        (repair / "batch-001" / name).write_text(__import__("json").dumps(repaired_output), encoding="utf-8")

    summary = preserve_compile_clean_units(
        previous_generation_run=previous,
        previous_verification_results=previous / "eval/verification-results.json",
        repair_run=repair,
        preserve_unit_keys={"unit-001"},
    )

    merged = __import__("json").loads((repair / "eval/merged-generation-output.json").read_text())
    first_batch = __import__("json").loads((repair / "batch-001/generation-output.json").read_text())
    second_batch = __import__("json").loads((repair / "batch-002/generation-output.json").read_text())
    assert summary["preserved_unit_keys"] == ["unit-001"]
    assert [unit["lean_file_body"] for unit in merged["units"]] == ["semantic-clean", "semantic-fixed"]
    assert [unit["unit_key"] for unit in first_batch["units"]] == ["unit-001"]
    assert [unit["unit_key"] for unit in second_batch["units"]] == ["unit-002"]


def test_semantic_key_helpers() -> None:
    semantic = {
        "units": [
            {"unit_key": "unit-001", "coverage_status": "all_aligned_gold_proved"},
            {"unit_key": "unit-002", "coverage_status": "partial_aligned_gold_proved"},
            {"unit_key": "unit-003", "coverage_status": "no_aligned_gold_proved"},
        ]
    }

    assert semantic_success_keys(semantic) == {"unit-001"}
    assert semantic_source_coverage_review_keys(semantic) == {"unit-002", "unit-003"}


def test_repair_loop_initial_semantic_results_drive_review_keys(monkeypatch, tmp_path: Path) -> None:
    args = _base_args(tmp_path)
    args.max_rounds = 1
    args.semantic_coverage = False
    semantic_path = tmp_path / "semantic.json"
    semantic_path.write_text(
        __import__("json").dumps(
            {
                "units": [
                    {"unit_key": "unit-001", "coverage_status": "all_aligned_gold_proved"},
                    {"unit_key": "unit-002", "coverage_status": "partial_aligned_gold_proved"},
                ]
            }
        ),
        encoding="utf-8",
    )
    args.initial_semantic_coverage_results = semantic_path
    seen_review_keys: list[list[str]] = []
    seen_preserved: list[set[str] | None] = []
    seen_repair_keys: list[list[str]] = []
    seen_repair_review_keys: list[list[str]] = []

    def fake_context_selection(namespace):
        seen_review_keys.append(list(namespace.source_coverage_review_unit_key))
        return {"valid_json": True}

    def fake_hydration(namespace):
        return {}

    def fake_pack(namespace):
        namespace.output.parent.mkdir(parents=True, exist_ok=True)
        namespace.output.write_text("{}", encoding="utf-8")
        return {}

    def fake_repair(namespace):
        seen_repair_keys.append(list(namespace.unit_key))
        seen_repair_review_keys.append(list(namespace.source_coverage_review_unit_key))
        (namespace.output / "batch-001").mkdir(parents=True, exist_ok=True)
        (namespace.output / "batch-001/generation-output.json").write_text('{"units":[]}', encoding="utf-8")
        return {}

    def fake_preserve(**kwargs):
        seen_preserved.append(kwargs.get("preserve_unit_keys"))
        return {}

    def fake_verify(namespace):
        return {"unit_count": 1, "compile_passed_units": 0}

    monkeypatch.setattr("scripts.run_latex_statement_repair_loop.run_context_selection", fake_context_selection)
    monkeypatch.setattr("scripts.run_latex_statement_repair_loop.run_hydration", fake_hydration)
    monkeypatch.setattr("scripts.run_latex_statement_repair_loop.run_context_pack", fake_pack)
    monkeypatch.setattr("scripts.run_latex_statement_repair_loop.run_repair", fake_repair)
    monkeypatch.setattr("scripts.run_latex_statement_repair_loop.preserve_compile_clean_units", fake_preserve)
    monkeypatch.setattr("scripts.run_latex_statement_repair_loop.run_verification", fake_verify)

    summary = run(args)

    assert summary["initial_semantic_coverage_results"] == str(semantic_path)
    assert seen_review_keys == [["unit-002"]]
    assert seen_repair_keys == [["unit-002"]]
    assert seen_repair_review_keys == [["unit-002"]]
    assert seen_preserved == [{"unit-001"}]
