"""Tests for theorem-level generation verification."""

import argparse
import json

from scripts.verify_latex_statement_generation import (
    available_support_candidate_names,
    build_lean_source,
    payload_context,
    run,
    run_lean_source,
    verify_generation_output,
    visible_support_candidates_by_unit,
    visible_support_candidates_for_unit,
)


def test_build_lean_source_adds_imports_and_opens() -> None:
    source = build_lean_source("theorem demo : True := by\n  trivial", imports=["Mathlib"], opens=["open Nat"])

    assert source.startswith("import Mathlib\nopen Nat\n")
    assert source.endswith("trivial\n")


def test_build_lean_source_closes_support_namespaces_before_body() -> None:
    source = build_lean_source(
        "theorem demo : True := by\n  trivial",
        imports=["Mathlib"],
        opens=[],
        support_context=["structure Box where\n  value : Nat\n\nnamespace Box\n\ndef get (b : Box) : Nat := b.value"],
    )

    assert "namespace Box" in source
    assert source.index("end Box") < source.index("theorem demo")


def test_run_lean_source_returns_structured_timeout(monkeypatch, tmp_path) -> None:
    import subprocess

    def fake_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(
            cmd=["lake", "env", "lean", "--stdin", "--json"],
            timeout=kwargs["timeout"],
            output="",
            stderr="partial stderr",
        )

    monkeypatch.setattr("scripts.verify_latex_statement_generation.subprocess.run", fake_run)

    result = run_lean_source("theorem demo : True := by trivial", project_root=tmp_path, timeout_seconds=0.01)

    assert result["returncode"] == 124
    assert result["messages"] == []
    assert "Lean command timed out after 0.01 seconds" in result["stderr"]


def test_visible_support_scopes_variables_to_matching_snippets() -> None:
    candidates = visible_support_candidates_for_unit(
        {
            "local_file_context_candidates": [
                {"kind": "variable", "name": "variable {K : Type*} [CommRing K]", "path": "A.lean"},
                {"kind": "variable", "name": "variable {K : Type*} [Field K] [Algebra ℚ K]", "path": "B.lean"},
                {"kind": "variable", "name": "variable (K) in", "path": "A.lean"},
            ],
            "planned_declarations": [
                {
                    "available_prior_project_context": [
                        {
                            "project_declarations": [
                                {
                                    "kind": "theorem",
                                    "name": "A.helper",
                                    "path": "A.lean",
                                    "lean_snippet": "theorem helper {K : Type*} [CommRing K] : True := by\n  trivial",
                                }
                            ]
                        }
                    ]
                }
            ],
        }
    )

    assert len(candidates) == 1
    assert candidates[0]["name"] == "A.helper"
    assert "variable {K : Type*} [CommRing K]" in candidates[0]["text"]
    assert "[Algebra ℚ K]" not in candidates[0]["text"]
    assert "variable (K) in" not in candidates[0]["text"]
    assert candidates[0]["text"].startswith("section\n")
    assert candidates[0]["text"].endswith("\nend")


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
    assert rows[0]["failure_class"] == "contract_violation"


def test_verify_generation_output_flags_generated_comments(monkeypatch, tmp_path) -> None:
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
                    "lean_file_body": "theorem demo : True := by\n  -- fill proof\n  trivial",
                }
            ]
        },
        project_root=tmp_path,
        imports=["Mathlib"],
        opens=[],
        timeout_seconds=1,
    )

    assert rows[0]["contract_violations"] == ["generated_lean_must_not_include_comments"]
    assert rows[0]["compile_passed"] is False


def test_verify_generation_output_flags_declaration_name_mismatch(monkeypatch, tmp_path) -> None:
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
                    "lean_file_body": (
                        "theorem demo : True := by\n  trivial\n\n"
                        "theorem extra : True := by\n  trivial"
                    ),
                }
            ]
        },
        project_root=tmp_path,
        imports=["Mathlib"],
        opens=[],
        timeout_seconds=1,
    )

    assert rows[0]["body_declaration_names"] == ["demo", "extra"]
    assert rows[0]["contract_violations"] == ["declaration_names_must_match_lean_file_body_declarations"]
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
    assert rows[0]["failure_class"] == "declined_cannot_prove"


def test_verify_generation_output_flags_cannot_prove_names_and_body(monkeypatch, tmp_path) -> None:
    def fake_run_lean_source(source, *, project_root, timeout_seconds):
        return {"returncode": 1, "messages": [], "stderr": ""}

    monkeypatch.setattr("scripts.verify_latex_statement_generation.run_lean_source", fake_run_lean_source)
    rows = verify_generation_output(
        {
            "units": [
                {
                    "unit_key": "unit-001",
                    "status": "cannot_prove_from_visible_context",
                    "declaration_names": ["bad_name"],
                    "lean_file_body": "theorem bad_name : True := by\n  trivial",
                }
            ]
        },
        project_root=tmp_path,
        imports=["Mathlib"],
        opens=[],
        timeout_seconds=1,
    )

    assert rows[0]["contract_violations"] == [
        "cannot_prove_output_must_have_empty_lean_file_body",
        "cannot_prove_output_must_have_empty_declaration_names",
    ]
    assert rows[0]["failure_class"] == "contract_violation"


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
                                                ],
                                                "local_file_context_candidates": [
                                                    {
                                                        "kind": "namespace",
                                                        "name": "AlgebraicCombinatorics.FPS",
                                                    }
                                                ],
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
                                                ],
                                                "local_file_context_candidates": [
                                                    {"kind": "namespace", "name": "Demo"}
                                                ],
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
    assert summary["failure_class_counts"] == {"compiled": 1}
    assert summary["batches"][0]["inferred_imports"] == ["Demo.Module"]
    assert summary["batches"][0]["inferred_opens"] == ["open Demo"]


def test_run_filters_inferred_open_statements_that_do_not_compile(monkeypatch, tmp_path) -> None:
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
                                                "local_file_context_candidates": [
                                                    {"kind": "namespace", "name": "Demo.Missing"},
                                                    {"kind": "namespace", "name": "Demo.Valid"},
                                                ],
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
    checked_sources: list[str] = []

    def fake_run_lean_source(source, *, project_root, timeout_seconds):
        checked_sources.append(source)
        if "open Demo.Missing" in source:
            return {
                "returncode": 1,
                "messages": [
                    {
                        "severity": "error",
                        "data": "unknown namespace `Demo.Missing`",
                        "line": 1,
                        "column": 0,
                    }
                ],
                "stderr": "",
            }
        return {"returncode": 0, "messages": [], "stderr": ""}

    monkeypatch.setattr("scripts.verify_latex_statement_generation.run_lean_source", fake_run_lean_source)
    summary = run(
        argparse.Namespace(
            generation_run=run_dir,
            project_root=tmp_path,
            imports=["Mathlib"],
            opens=[],
            infer_context=True,
            filter_target_module_imports=True,
            materialize_visible_support=False,
            timeout_seconds=1.0,
            output=run_dir / "eval/verification-results.json",
        )
    )

    final_source = checked_sources[-1]
    assert "open Demo.Missing" not in final_source
    assert "open Demo.Valid" in final_source
    batch_summary = summary["batches"][0]
    assert batch_summary["inferred_opens"] == ["open Demo.Valid"]
    assert [
        row["open_statement"] for row in batch_summary["filtered_invalid_inferred_opens"]
    ] == ["open Demo.Missing"]
    assert summary["compile_passed_units"] == 1


def test_run_summarizes_cannot_prove_failure_class(monkeypatch, tmp_path) -> None:
    run_dir = tmp_path / "run"
    batch = run_dir / "batch-001"
    batch.mkdir(parents=True)
    (batch / "generation-output.json").write_text(
        json.dumps(
            {
                "units": [
                    {
                        "unit_key": "unit-001",
                        "status": "cannot_prove_from_visible_context",
                        "declaration_names": [],
                        "lean_file_body": "",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    (batch / "generation-payload.json").write_text(
        json.dumps({"messages": [{"role": "user", "content": json.dumps({"units": []})}]}),
        encoding="utf-8",
    )

    def fail_if_called(source, *, project_root, timeout_seconds):
        raise AssertionError("Lean should not run for empty cannot-prove outputs")

    monkeypatch.setattr("scripts.verify_latex_statement_generation.run_lean_source", fail_if_called)
    summary = run(
        argparse.Namespace(
            generation_run=run_dir,
            project_root=tmp_path,
            imports=["Mathlib"],
            opens=[],
            infer_context=True,
            filter_target_module_imports=True,
            materialize_visible_support=False,
            timeout_seconds=1.0,
            output=run_dir / "eval/verification-results.json",
        )
    )

    assert summary["compile_passed_units"] == 0
    assert summary["failure_class_counts"] == {"declined_cannot_prove": 1}
    assert summary["batches"][0]["failure_class_counts"] == {"declined_cannot_prove": 1}


def test_run_filters_hidden_target_module_imports(monkeypatch, tmp_path) -> None:
    selector_run = tmp_path / "selector"
    (selector_run / "eval").mkdir(parents=True)
    (selector_run / "eval/selected-units.jsonl").write_text(
        json.dumps(
            {
                "id": "Demo.tex:target",
                "posthoc_lean_alignment": {
                    "aligned_lean_declarations": [
                        {
                            "full_name": "Demo.TargetModule.hidden_target",
                            "module": "Demo.TargetModule",
                            "path": "Demo/TargetModule.lean",
                        }
                    ]
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )

    run_dir = tmp_path / "run"
    batch = run_dir / "batch-001"
    batch.mkdir(parents=True)
    wrapper = tmp_path / "Demo/Wrapper.lean"
    wrapper.parent.mkdir()
    wrapper.write_text("import Demo.TargetModule\n", encoding="utf-8")
    (run_dir / "eval").mkdir()
    (run_dir / "eval/generation-results.json").write_text(
        json.dumps({"selector_run": str(selector_run)}),
        encoding="utf-8",
    )
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
                                                "local_file_context_candidates": [
                                                    {"kind": "namespace", "name": "Demo.TargetModule"},
                                                    {"kind": "namespace", "name": "TargetModule"},
                                                    {"kind": "namespace", "name": "Demo.Wrapper"},
                                                    {"kind": "namespace", "name": "Wrapper"},
                                                    {"kind": "namespace", "name": "Demo.Prior"},
                                                ],
                                                "available_prior_project_context": [
                                                    {
                                                        "project_declarations": [
                                                            {
                                                                "name": "Demo.TargetModule.hidden_target",
                                                                "module": "Demo.TargetModule",
                                                            },
                                                            {
                                                                "name": "Demo.Wrapper.allowed_looking",
                                                                "module": "Demo.Wrapper",
                                                            },
                                                            {
                                                                "name": "Demo.Prior.helper",
                                                                "module": "Demo.Prior",
                                                            },
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
        assert "import Demo.Prior" in source
        assert "import Demo.TargetModule" not in source
        assert "import Demo.Wrapper" not in source
        assert "open Demo.TargetModule" not in source
        assert "open TargetModule" not in source
        assert "open Demo.Wrapper" not in source
        assert "open Wrapper" not in source
        assert "open Demo.Prior" in source
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

    batch_summary = summary["batches"][0]
    assert batch_summary["unfiltered_inferred_imports"] == ["Demo.TargetModule", "Demo.Wrapper", "Demo.Prior"]
    assert batch_summary["inferred_imports"] == ["Demo.Prior"]
    assert batch_summary["hidden_target_modules"] == ["Demo.TargetModule"]
    assert batch_summary["filtered_target_module_imports"] == ["Demo.TargetModule", "Demo.Wrapper"]
    assert batch_summary["hidden_target_namespaces"] == ["Demo.TargetModule"]
    assert batch_summary["filtered_target_namespace_opens"] == [
        "open Demo.TargetModule",
        "open TargetModule",
        "open Demo.Wrapper",
        "open Wrapper",
    ]
    assert batch_summary["inferred_opens"] == ["open Demo.Prior"]
    assert summary["compile_passed_units"] == 1


def test_run_uses_proof_lane_summary_selector_for_hidden_target_filter(monkeypatch, tmp_path) -> None:
    selector_run = tmp_path / "selector"
    (selector_run / "eval").mkdir(parents=True)
    (selector_run / "eval/selected-units.jsonl").write_text(
        json.dumps(
            {
                "id": "Demo.tex:target",
                "posthoc_lean_alignment": {
                    "aligned_lean_declarations": [
                        {
                            "full_name": "Demo.TargetModule.hidden_target",
                            "module": "Demo.TargetModule",
                            "path": "Demo/TargetModule.lean",
                        }
                    ]
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )
    proof_lane_tasks = tmp_path / "proof-lane-tasks"
    proof_lane_tasks.mkdir()
    (proof_lane_tasks / "proof-lane-summary.json").write_text(
        json.dumps({"selector_run": str(selector_run)}),
        encoding="utf-8",
    )

    run_dir = tmp_path / "run"
    batch = run_dir / "batch-001"
    batch.mkdir(parents=True)
    (run_dir / "eval").mkdir()
    (run_dir / "eval/generation-results.json").write_text(
        json.dumps({"proof_lane_task_dir": str(proof_lane_tasks)}),
        encoding="utf-8",
    )
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
                                "proof_lane_tasks": [
                                    {
                                        "visible_prompt_context": {
                                            "planned_declarations": [
                                                {
                                                    "available_prior_project_context": [
                                                        {
                                                            "project_declarations": [
                                                                {
                                                                    "name": "Demo.TargetModule.hidden_target",
                                                                    "module": "Demo.TargetModule",
                                                                },
                                                                {
                                                                    "name": "Demo.Prior.helper",
                                                                    "module": "Demo.Prior",
                                                                },
                                                            ]
                                                        }
                                                    ]
                                                }
                                            ]
                                        }
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
        assert "import Demo.TargetModule" not in source
        assert "import Demo.Prior" in source
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
            filter_target_module_imports=True,
        )
    )

    assert summary["batches"][0]["hidden_target_modules"] == ["Demo.TargetModule"]
    assert summary["batches"][0]["inferred_imports"] == ["Demo.Prior"]


def test_run_can_materialize_visible_support_snippets(monkeypatch, tmp_path) -> None:
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
                        "declaration_names": ["generated"],
                        "lean_file_body": "theorem generated : True := prior_helper",
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
                                        "unit_key": "unit-001",
                                        "planned_declarations": [
                                            {
                                                "available_prior_project_context": [
                                                    {
                                                        "project_declarations": [
                                                            {
                                                                "kind": "theorem",
                                                                "name": "prior_helper",
                                                                "lean_snippet": "theorem prior_helper : True := by\n  trivial",
                                                            },
                                                            {
                                                                "kind": "theorem",
                                                                "name": "prior_ext",
                                                                "lean_snippet": "@[ext]\ntheorem prior_ext : True := by\n  trivial",
                                                            },
                                                            {
                                                                "kind": "lemma",
                                                                "name": "partial_helper",
                                                                "lean_snippet": "lemma partial_helper : True",
                                                            },
                                                        ]
                                                    }
                                                ]
                                            }
                                        ],
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
    calls: list[str] = []

    def fake_run_lean_source(source, *, project_root, timeout_seconds):
        calls.append(source)
        return {"returncode": 0, "messages": [], "stderr": ""}

    monkeypatch.setattr("scripts.verify_latex_statement_generation.run_lean_source", fake_run_lean_source)
    summary = run(
        argparse.Namespace(
            generation_run=run_dir,
            project_root=tmp_path,
            imports=["Mathlib"],
            opens=[],
            infer_context=True,
            filter_target_module_imports=True,
            materialize_visible_support=True,
            support_timeout_seconds=1.0,
            timeout_seconds=1.0,
            output=run_dir / "eval/verification-results.json",
        )
    )

    final_source = calls[-1]
    assert "theorem prior_helper : True" in final_source
    assert "@[ext]\ntheorem prior_ext : True" in final_source
    assert final_source.index("theorem prior_helper") < final_source.index("theorem generated")
    assert "partial_helper" not in final_source
    support = summary["batches"][0]["units"][0]["visible_support_context"]
    assert support["candidate_count"] == 2
    assert support["accepted_count"] == 2
    assert support["rejected_count"] == 0
    assert support["lean_call_count"] == 1
    assert support["materialization_strategy"] == "batched"
    assert len(calls) == 2


def test_run_can_materialize_visible_support_as_assumptions(monkeypatch, tmp_path) -> None:
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
                        "declaration_names": ["generated"],
                        "lean_file_body": "theorem generated : True := helper_missing",
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
                                        "unit_key": "unit-001",
                                        "planned_declarations": [
                                            {
                                                "available_prior_project_context": [
                                                    {
                                                        "project_declarations": [
                                                            {
                                                                "kind": "theorem",
                                                                "name": "helper_missing",
                                                                "lean_snippet": "theorem helper_missing : True := by\n  trivial",
                                                            },
                                                            {
                                                                "kind": "theorem",
                                                                "name": "helper_available",
                                                                "lean_snippet": "theorem helper_available : True := by\n  trivial",
                                                            },
                                                        ]
                                                    }
                                                ]
                                            }
                                        ],
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
    calls: list[str] = []

    def fake_run_lean_source(source, *, project_root, timeout_seconds):
        calls.append(source)
        messages = []
        for line_number, line in enumerate(source.splitlines(), start=1):
            if line == "#check helper_missing":
                messages.append({"severity": "error", "line": line_number, "data": "unknown helper_missing"})
        return {"returncode": 1 if messages else 0, "messages": messages, "stderr": ""}

    monkeypatch.setattr("scripts.verify_latex_statement_generation.run_lean_source", fake_run_lean_source)
    summary = run(
        argparse.Namespace(
            generation_run=run_dir,
            project_root=tmp_path,
            imports=["Mathlib"],
            opens=[],
            infer_context=True,
            filter_target_module_imports=True,
            materialize_visible_support=True,
            support_mode="assumption",
            support_timeout_seconds=1.0,
            timeout_seconds=1.0,
            output=run_dir / "eval/verification-results.json",
        )
    )

    final_source = calls[-1]
    assert "axiom helper_missing : True" in final_source
    assert "helper_available" not in final_source
    support = summary["batches"][0]["units"][0]["visible_support_context"]
    assert support["support_mode"] == "assumption"
    assert support["candidate_count"] == 2
    assert support["accepted_count"] == 1
    assert support["skipped_count"] == 1
    assert support["availability_lean_call_count"] == 1
    assert support["materialization_lean_call_count"] == 1
    assert support["lean_call_count"] == 2
    assert support["materialization_strategy"] == "batched"


def test_run_checks_visible_support_assumptions_before_injecting(monkeypatch, tmp_path) -> None:
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
                        "declaration_names": ["generated"],
                        "lean_file_body": "theorem generated : True := helper_good",
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
                                        "unit_key": "unit-001",
                                        "planned_declarations": [
                                            {
                                                "available_prior_project_context": [
                                                    {
                                                        "project_declarations": [
                                                            {
                                                                "kind": "theorem",
                                                                "name": "helper_good",
                                                                "lean_snippet": "theorem helper_good : True := by\n  trivial",
                                                            },
                                                            {
                                                                "kind": "theorem",
                                                                "name": "helper_bad",
                                                                "lean_snippet": "theorem helper_bad (x : MissingType) : True := by\n  trivial",
                                                            },
                                                        ]
                                                    }
                                                ]
                                            }
                                        ],
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
    calls: list[str] = []

    def fake_run_lean_source(source, *, project_root, timeout_seconds):
        calls.append(source)
        messages = []
        for line_number, line in enumerate(source.splitlines(), start=1):
            if line == "#check helper_good" or line == "#check helper_bad":
                messages.append({"severity": "error", "line": line_number, "data": "unknown support name"})
            if "MissingType" in line:
                messages.append({"severity": "error", "line": line_number, "data": "unknown MissingType"})
        return {"returncode": 1 if messages else 0, "messages": messages, "stderr": ""}

    monkeypatch.setattr("scripts.verify_latex_statement_generation.run_lean_source", fake_run_lean_source)
    summary = run(
        argparse.Namespace(
            generation_run=run_dir,
            project_root=tmp_path,
            imports=["Mathlib"],
            opens=[],
            infer_context=True,
            filter_target_module_imports=True,
            materialize_visible_support=True,
            support_mode="assumption",
            support_timeout_seconds=1.0,
            timeout_seconds=1.0,
            output=run_dir / "eval/verification-results.json",
        )
    )

    final_source = calls[-1]
    assert "axiom helper_good : True" in final_source
    assert "helper_bad" not in final_source
    support = summary["batches"][0]["units"][0]["visible_support_context"]
    assert support["accepted_count"] == 1
    assert support["rejected_count"] == 1
    assert [row["name"] for row in support["rejected"]] == ["helper_bad"]
    assert support["availability_lean_call_count"] == 1
    assert support["materialization_lean_call_count"] == 2
    assert support["lean_call_count"] == 3
    assert support["materialization_strategy"] == "batched"
    assert summary["compile_passed_units"] == 1


def test_visible_support_candidates_read_proof_lane_tasks(tmp_path) -> None:
    batch = tmp_path / "run/batch-001"
    batch.mkdir(parents=True)
    raw_output = batch / "raw-generation-output.json"
    raw_output.write_text('{"units":[]}\n', encoding="utf-8")
    (batch / "generation-payload.json").write_text(
        json.dumps(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": json.dumps(
                            {
                                "proof_lane_tasks": [
                                    {
                                        "unit_key": "unit-007",
                                        "decline_context_pack": {
                                            "selected_project_context": [
                                                {
                                                    "kind": "def",
                                                    "name": "Demo.helper",
                                                    "lean_snippet": "def helper : Nat := 0",
                                                }
                                            ]
                                        },
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

    candidates = visible_support_candidates_by_unit(raw_output)

    assert list(candidates) == ["unit-007"]
    assert candidates["unit-007"][0]["name"] == "Demo.helper"
    assert candidates["unit-007"][0]["text"] == "def helper : Nat := 0"


def test_visible_support_snippet_trims_trailing_namespace_directives() -> None:
    candidates = visible_support_candidates_for_unit(
        {
            "planned_declarations": [
                {
                    "available_prior_project_context": [
                        {
                            "project_declarations": [
                                {
                                    "kind": "structure",
                                    "name": "Demo.Box",
                                    "lean_snippet": "\n".join(
                                        [
                                            "structure Box where",
                                            "  value : Nat",
                                            "",
                                            "namespace Box",
                                            "variable {α : Type*}",
                                            "def leaked : Nat := 1",
                                        ]
                                    ),
                                }
                            ]
                        }
                    ]
                }
            ]
        }
    )

    assert candidates[0]["text"] == "structure Box where\n  value : Nat"


def test_visible_support_assumption_mode_keeps_theorem_signatures() -> None:
    candidates = visible_support_candidates_for_unit(
        {
            "planned_declarations": [
                {
                    "available_prior_project_context": [
                        {
                            "project_declarations": [
                                {
                                    "kind": "theorem",
                                    "name": "Demo.helper",
                                    "lean_snippet": "theorem helper (n : Nat) : n = n",
                                },
                                {
                                    "kind": "lemma",
                                    "name": "Demo.partial",
                                    "lean_snippet": "private lemma partial (n : Nat) : n = n := by\n  rfl",
                                },
                            ]
                        }
                    ]
                }
            ]
        },
        assumption_mode=True,
    )

    texts = [candidate["text"] for candidate in candidates]
    assert "namespace Demo\naxiom helper (n : Nat) : n = n\nend Demo" in texts
    assert "namespace Demo\naxiom partial (n : Nat) : n = n\nend Demo" in texts


def test_visible_support_assumption_mode_wraps_relative_dotted_names() -> None:
    candidates = visible_support_candidates_for_unit(
        {
            "planned_declarations": [
                {
                    "available_prior_project_context": [
                        {
                            "project_declarations": [
                                {
                                    "kind": "def",
                                    "name": "LGV1.LatticeStep.apply",
                                    "lean_snippet": (
                                        "def LatticeStep.apply (s : LatticeStep) "
                                        "(p : LatticePoint) : LatticePoint := p"
                                    ),
                                },
                                {
                                    "kind": "def",
                                    "name": "LatticeStep.rootApply",
                                    "lean_snippet": (
                                        "def LatticeStep.rootApply (s : LatticeStep) "
                                        "(p : LatticePoint) : LatticePoint := p"
                                    ),
                                },
                            ]
                        }
                    ]
                }
            ]
        },
        assumption_mode=True,
    )

    texts = [candidate["text"] for candidate in candidates]
    assert (
        "namespace LGV1\n"
        "axiom LatticeStep.apply (s : LatticeStep) (p : LatticePoint) : LatticePoint\n"
        "end LGV1"
    ) in texts
    assert (
        "axiom LatticeStep.rootApply (s : LatticeStep) (p : LatticePoint) : LatticePoint"
    ) in texts


def test_visible_support_assumption_mode_preserves_type_alias_abbrevs() -> None:
    candidates = visible_support_candidates_for_unit(
        {
            "planned_declarations": [
                {
                    "available_prior_project_context": [
                        {
                            "project_declarations": [
                                {
                                    "kind": "abbrev",
                                    "name": "LGV1.LatticePoint",
                                    "lean_snippet": "abbrev LatticePoint := ℤ × ℤ",
                                },
                                {
                                    "kind": "abbrev",
                                    "name": "Demo.h",
                                    "lean_snippet": "noncomputable abbrev h (n : ℕ) : Nat := n",
                                },
                            ]
                        }
                    ]
                }
            ]
        },
        assumption_mode=True,
    )

    texts = [candidate["text"] for candidate in candidates]
    assert "namespace LGV1\nabbrev LatticePoint := ℤ × ℤ\nend LGV1" in texts
    assert "namespace Demo\naxiom h (n : ℕ) : Nat\nend Demo" in texts


def test_visible_support_assumption_mode_splits_only_top_level_body_markers() -> None:
    candidates = visible_support_candidates_for_unit(
        {
            "planned_declarations": [
                {
                    "available_prior_project_context": [
                        {
                            "project_declarations": [
                                {
                                    "kind": "def",
                                    "name": "LGV.nipatSetFinite",
                                    "lean_snippet": (
                                        "noncomputable def nipatSetFinite {D : SimpleDigraph V} "
                                        ": Set.Finite (nipatSet (D := D) A B) := by\n"
                                        "  trivial"
                                    ),
                                },
                                {
                                    "kind": "def",
                                    "name": "LGV.dyckDigraph",
                                    "lean_snippet": (
                                        "def dyckDigraph : SimpleDigraph (ℤ × ℕ) where\n"
                                        "  arc u v := True"
                                    ),
                                },
                            ]
                        }
                    ]
                }
            ]
        },
        assumption_mode=True,
    )

    texts = [candidate["text"] for candidate in candidates]
    assert (
        "namespace LGV\n"
        "axiom nipatSetFinite {D : SimpleDigraph V} : Set.Finite (nipatSet (D := D) A B)\n"
        "end LGV"
    ) in texts
    assert "namespace LGV\naxiom dyckDigraph : SimpleDigraph (ℤ × ℕ)\nend LGV" in texts


def test_visible_support_snippet_trims_trailing_attributes() -> None:
    candidates = visible_support_candidates_for_unit(
        {
            "planned_declarations": [
                {
                    "available_prior_project_context": [
                        {
                            "project_declarations": [
                                {
                                    "kind": "structure",
                                    "name": "LGV.PathTuple",
                                    "lean_snippet": "\n".join(
                                        [
                                            "structure PathTuple where",
                                            "  paths : Nat",
                                            "",
                                            "@[ext]",
                                            "lemma PathTuple.ext : True := by trivial",
                                        ]
                                    ),
                                }
                            ]
                        }
                    ]
                }
            ]
        },
        assumption_mode=True,
    )

    assert candidates[0]["text"] == "namespace LGV\nstructure PathTuple where\n  paths : Nat\nend LGV"


def test_visible_support_resolves_full_name_from_source_line(tmp_path) -> None:
    project = tmp_path / "project"
    source = project / "AlgebraicCombinatorics/Determinants/LGV2.lean"
    source.parent.mkdir(parents=True)
    source.write_text(
        "\n".join(
            [
                "namespace LGV",
                "",
                "theorem helper : True := by trivial",
                "",
                "def translatePath : Nat := 0",
                "",
                "end LGV",
            ]
        ),
        encoding="utf-8",
    )

    candidates = visible_support_candidates_for_unit(
        {
            "planned_declarations": [
                {
                    "local_file_predecessor_declarations": [
                        {
                            "kind": "def",
                            "name": "translatePath",
                            "path": "AlgebraicCombinatorics/Determinants/LGV2.lean",
                            "line_range": [5, 5],
                            "lean_snippet": "def translatePath : Nat := 0",
                        }
                    ]
                }
            ]
        },
        assumption_mode=True,
        project_root=project,
    )

    assert candidates[0]["name"] == "LGV.translatePath"
    assert candidates[0]["text"] == "namespace LGV\naxiom translatePath : Nat\nend LGV"


def test_available_support_candidate_names_batches_checks(monkeypatch, tmp_path) -> None:
    def fake_run_lean_source(source, *, project_root, timeout_seconds):
        messages = []
        for line_number, line in enumerate(source.splitlines(), start=1):
            if line == "#check Demo.missing":
                messages.append(
                    {
                        "severity": "error",
                        "line": line_number,
                        "column": 8,
                        "data": "Unknown identifier `Demo.missing`",
                    }
                )
        return {"returncode": 1, "messages": messages, "stderr": ""}

    monkeypatch.setattr("scripts.verify_latex_statement_generation.run_lean_source", fake_run_lean_source)

    availability = available_support_candidate_names(
        [
            {"name": "Demo.available", "text": "axiom available : Nat"},
            {"name": "Demo.missing", "text": "axiom missing : Nat"},
        ],
        project_root=tmp_path,
        imports=["Mathlib"],
        opens=[],
        timeout_seconds=1,
    )

    assert availability == {"Demo.available": True, "Demo.missing": False}
