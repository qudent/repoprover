"""Tests for partial-proof diagnostic artifacts."""

import argparse
import json
from pathlib import Path

import scripts.diagnose_latex_statement_partial_proofs as diagnose


def test_partial_proof_diagnostic_classifies_sorry_body(monkeypatch, tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    batch = run_dir / "batch-001"
    batch.mkdir(parents=True)
    (batch / "raw-generation-output.json").write_text(
        json.dumps(
            {
                "units": [
                    {
                        "unit_key": "unit-001",
                        "status": "cannot_prove_from_visible_context",
                        "declaration_names": ["demo"],
                        "lean_file_body": "theorem demo : True := by\n  sorry",
                        "used_context": ["Demo.helper"],
                        "notes": ["missing final proof"],
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
                                        "unit_key": "unit-001",
                                        "source_unit": {
                                            "id": "tex/demo.tex:thm.demo",
                                            "path": "AlgebraicCombinatorics/tex/Demo/Target.tex",
                                        },
                                        "visible_prompt_context": {
                                            "planned_declarations": [
                                                {
                                                    "available_prior_project_context": [
                                                        {
                                                                    "project_declarations": [
                                                                {
                                                                    "name": "Demo.hidden",
                                                                    "module": "AlgebraicCombinatorics.Demo.Target",
                                                                },
                                                                {
                                                                    "name": "Demo.wrapper",
                                                                    "module": "AlgebraicCombinatorics.Demo.Wrapper",
                                                                }
                                                            ]
                                                        }
                                                    ]
                                                }
                                            ]
                                        },
                                        "decline_context_pack": {
                                            "selected_project_context": [
                                                {
                                                    "kind": "theorem",
                                                    "name": "Demo.helper",
                                                    "lean_snippet": "theorem helper : True := by\n  trivial",
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
    wrapper = tmp_path / "AlgebraicCombinatorics/Demo/Wrapper.lean"
    wrapper.parent.mkdir(parents=True)
    wrapper.write_text("import AlgebraicCombinatorics.Demo.Target\n", encoding="utf-8")
    seen_sources: list[str] = []

    def fake_run_lean_source(source, *, project_root, timeout_seconds):
        seen_sources.append(source)
        return {"returncode": 0, "messages": [], "stderr": ""}

    monkeypatch.setattr(diagnose.verify, "run_lean_source", fake_run_lean_source)
    summary = diagnose.run(
        argparse.Namespace(
            generation_run=[run_dir],
            unit_key=None,
            output=tmp_path / "diagnostic",
            project_root=tmp_path,
            imports=["Mathlib"],
            opens=[],
            infer_context=True,
            filter_source_module_imports=True,
            validate_inferred_opens=True,
            open_timeout_seconds=1.0,
            materialize_visible_support=True,
            support_timeout_seconds=1.0,
            timeout_seconds=1.0,
            include_empty_raw_units=False,
        )
    )

    assert summary["diagnostic_class_counts"] == {"lean_accepts_with_placeholder": 1}
    unit = summary["units"][0]
    assert unit["source_unit_id"] == "tex/demo.tex:thm.demo"
    assert unit["visible_support_context"]["candidate_count"] == 1
    assert unit["visible_support_context"]["accepted_count"] == 1
    assert all("import AlgebraicCombinatorics.Demo.Target" not in source for source in seen_sources)
    assert all("import AlgebraicCombinatorics.Demo.Wrapper" not in source for source in seen_sources)
    assert summary["raw_files"][0]["filtered_source_module_imports"] == [
        "AlgebraicCombinatorics.Demo.Target",
        "AlgebraicCombinatorics.Demo.Wrapper",
    ]
    assert "theorem helper : True" in seen_sources[-1]
    assert (tmp_path / "diagnostic/partial-proof-diagnostics.json").exists()
    assert (tmp_path / "diagnostic/partial-proof-diagnostics.md").exists()
