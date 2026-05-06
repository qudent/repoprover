"""Tests for theorem-level generation verification."""

import argparse
import json

from scripts.verify_latex_statement_generation import build_lean_source, payload_context, run, verify_generation_output


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
