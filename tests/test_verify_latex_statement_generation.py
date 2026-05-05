"""Tests for theorem-level generation verification."""

import argparse
import json

from scripts.verify_latex_statement_generation import build_lean_source, payload_context, run, verify_generation_output


def test_build_lean_source_adds_imports_and_opens() -> None:
    source = build_lean_source("theorem demo : True := by\n  trivial", imports=["Mathlib"], opens=["open Nat"])

    assert source.startswith("import Mathlib\nopen Nat\n")
    assert source.endswith("trivial\n")


def test_verify_generation_output_classifies_placeholders(monkeypatch, tmp_path) -> None:
    def fake_run_lean_source(source, *, project_root, timeout_seconds):
        return {"returncode": 0, "messages": [], "stderr": ""}

    monkeypatch.setattr("scripts.verify_latex_statement_generation.run_lean_source", fake_run_lean_source)
    rows = verify_generation_output(
        {
            "units": [
                {
                    "unit_key": "unit-001",
                    "status": "generated",
                    "declaration_names": ["demo"],
                    "lean_file_body": "theorem demo : True := by\n  sorry",
                }
            ]
        },
        project_root=tmp_path,
        imports=["Mathlib"],
        opens=[],
        timeout_seconds=1,
    )

    assert rows[0]["placeholder_tokens"] == ["sorry"]
    assert rows[0]["contract_violations"] == ["generated_lean_contains_placeholder"]
    assert rows[0]["lean_returncode"] == 0
    assert rows[0]["compile_passed"] is False


def test_verify_generation_output_skips_empty_cannot_prove(monkeypatch, tmp_path) -> None:
    def fail_if_called(source, *, project_root, timeout_seconds):
        raise AssertionError("Lean should not run for empty cannot-prove outputs")

    monkeypatch.setattr("scripts.verify_latex_statement_generation.run_lean_source", fail_if_called)
    rows = verify_generation_output(
        {
            "units": [
                {
                    "unit_key": "unit-001",
                    "status": "cannot_prove_from_visible_context",
                    "declaration_names": [],
                    "lean_file_body": "",
                }
            ]
        },
        project_root=tmp_path,
        imports=["Mathlib"],
        opens=[],
        timeout_seconds=1,
    )

    assert rows[0]["reported_status"] == "cannot_prove_from_visible_context"
    assert rows[0]["skipped_reason"] == "cannot_prove_from_visible_context"
    assert rows[0]["compile_passed"] is False


def test_payload_context_infers_project_imports_and_opens(tmp_path) -> None:
    batch = tmp_path / "run/batch-001"
    batch.mkdir(parents=True)
    output = batch / "generation-output.json"
    output.write_text('{"units":[]}\n', encoding="utf-8")
    (batch / "generation-payload.json").write_text(
        json.dumps(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": json.dumps(
                            {
                                "units": [
                                    {
                                        "planned_declarations": [
                                            {
                                                "available_prior_project_context": [
                                                    {
                                                        "project_declarations": [
                                                            {
                                                                "name": "AlgebraicCombinatorics.FPS.IsInverse",
                                                                "module": "AlgebraicCombinatorics.FPS.CommutativeRings",
                                                                "imports": ["Mathlib"],
                                                            }
                                                        ]
                                                    }
                                                ]
                                            }
                                        ]
                                    }
                                ]
                            }
                        ),
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    context = payload_context(output)

    assert "AlgebraicCombinatorics.FPS.CommutativeRings" in context["imports"]
    assert "open AlgebraicCombinatorics.FPS" in context["opens"]


def test_run_uses_inferred_context(monkeypatch, tmp_path) -> None:
    run_dir = tmp_path / "run"
    batch = run_dir / "batch-001"
    batch.mkdir(parents=True)
    (batch / "generation-output.json").write_text(
        json.dumps(
            {
                "units": [
                    {
                        "unit_key": "unit-001",
                        "status": "generated",
                        "declaration_names": ["demo"],
                        "lean_file_body": "theorem demo : True := by\n  trivial",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    (batch / "generation-payload.json").write_text(
        json.dumps(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": json.dumps(
                            {
                                "units": [
                                    {
                                        "planned_declarations": [
                                            {
                                                "available_prior_project_context": [
                                                    {
                                                        "project_declarations": [
                                                            {
                                                                "name": "Demo.Prior",
                                                                "module": "Demo.Module",
                                                                "imports": ["Mathlib"],
                                                            }
                                                        ]
                                                    }
                                                ]
                                            }
                                        ]
                                    }
                                ]
                            }
                        ),
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    def fake_run_lean_source(source, *, project_root, timeout_seconds):
        assert "import Demo.Module" in source
        assert "open Demo" in source
        return {"returncode": 0, "messages": [], "stderr": ""}

    monkeypatch.setattr("scripts.verify_latex_statement_generation.run_lean_source", fake_run_lean_source)
    summary = run(
        argparse.Namespace(
            generation_run=run_dir,
            project_root=tmp_path,
            imports=["Mathlib"],
            opens=[],
            infer_context=True,
            timeout_seconds=1.0,
            output=run_dir / "eval/verification-results.json",
        )
    )

    assert summary["compile_passed_units"] == 1
    assert summary["batches"][0]["inferred_imports"] == ["Demo.Module"]
    assert summary["batches"][0]["inferred_opens"] == ["open Demo"]
