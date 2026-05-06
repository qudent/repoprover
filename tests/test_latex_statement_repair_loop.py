"""Tests for the bounded theorem-level repair-loop runner."""

import argparse
from pathlib import Path

from scripts.run_latex_statement_repair_loop import run


def _base_args(tmp_path: Path) -> argparse.Namespace:
    initial_generation = tmp_path / "initial-generation"
    initial_verification = initial_generation / "eval" / "verification-results.json"
    initial_verification.parent.mkdir(parents=True)
    initial_verification.write_text('{"unit_count":1,"compile_passed_units":0}\n', encoding="utf-8")
    return argparse.Namespace(
        selector_run=tmp_path / "selector",
        initial_generation_run=initial_generation,
        initial_verification_results=initial_verification,
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
    calls: list[str] = []
    repair_extra_contexts: list[list[Path]] = []

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

    assert summary["stop_reason"] == "all_units_compile"
    assert summary["final_generation_run"] == str(args.output_root / "round-01-repair")
    assert calls == ["context", "hydration", "pack", "repair", "verify", "gold", "semantic"]
    assert repair_extra_contexts == [[args.output_root / "round-01-context" / "checked-repair-context.json"]]
