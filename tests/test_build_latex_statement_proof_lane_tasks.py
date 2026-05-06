"""Tests for target-hidden proof-lane task dossier generation."""

import argparse
import json
from pathlib import Path

from scripts.build_latex_statement_proof_lane_tasks import run


def test_builds_declined_task_without_posthoc_gold(tmp_path: Path) -> None:
    selector = tmp_path / "selector"
    generation = tmp_path / "generation"
    output = tmp_path / "proof-lane"
    (selector / "eval").mkdir(parents=True)
    (generation / "batch-001").mkdir(parents=True)
    (generation / "eval").mkdir()

    selected = {
        "id": "source:demo",
        "source_unit": {
            "environment": "lemma",
            "path": "Demo.tex",
            "line_range": [1, 2],
            "labels": ["demo"],
            "referenced_labels": [],
            "part_markers": [],
            "parse_warnings": [],
            "source_text": "\\begin{lemma}\\label{demo}Demo source.\\end{lemma}",
        },
        "posthoc_lean_alignment": {
            "aligned_lean_declarations": [{"full_name": "Demo.hidden_gold"}]
        },
    }
    (selector / "eval/selected-units.jsonl").write_text(json.dumps(selected) + "\n", encoding="utf-8")
    (generation / "eval/generation-results.json").write_text(
        json.dumps({"selector_run": str(selector)}),
        encoding="utf-8",
    )
    (generation / "batch-001/generation-output.json").write_text(
        json.dumps(
            {
                "units": [
                    {
                        "unit_key": "unit-001",
                        "status": "cannot_prove_from_visible_context",
                        "lean_file_body": "",
                        "declaration_names": [],
                        "notes": ["missing visible helper"],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    prompt_user = {
        "units": [
            {
                "unit_key": "unit-001",
                "source_focus_summary": "demo focus",
                "previous_source_context": [{"source_unit": {"id": "source:prior"}}],
                "planned_declarations": [
                    {
                        "task_id": "unit-001-task-1",
                        "kind": "theorem",
                        "role": "main_claim",
                        "source_part": "whole unit",
                        "selector_unchecked_statement_sketch": "demo theorem",
                        "hydrated_mathlib_context": [
                            {
                                "exact_identifier": "Nat.add_zero",
                                "lean_check": {"status": "checked", "signature": "Nat.add_zero ..."},
                            }
                        ],
                    }
                ],
            }
        ]
    }
    (generation / "batch-001/generation-payload.json").write_text(
        json.dumps({"messages": [{"role": "user", "content": json.dumps(prompt_user)}]}),
        encoding="utf-8",
    )
    verification_path = generation / "eval/verification-results.json"
    verification_path.write_text(
        json.dumps(
            {
                "batches": [
                    {
                        "units": [
                            {
                                "unit_key": "unit-001",
                                "compile_passed": False,
                                "failure_class": "declined_cannot_prove",
                                "reported_status": "cannot_prove_from_visible_context",
                                "skipped_reason": "cannot_prove_from_visible_context",
                                "visible_support_context": {"accepted": [{"name": "Demo.visible"}]},
                            }
                        ]
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    semantic_path = generation / "eval/semantic-coverage.json"
    semantic_path.write_text(
        json.dumps(
            {
                "units": [
                    {
                        "unit_key": "unit-001",
                        "source_unit_id": "source:demo",
                        "compile_passed": False,
                        "coverage_status": "generated_not_compiled",
                        "aligned_gold_declaration_count": 1,
                        "semantic_passed_gold_declarations": [],
                        "checks": [{"gold_full_name": "Demo.hidden_gold"}],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    summary = run(
        argparse.Namespace(
            generation_run=generation,
            verification_results=verification_path,
            semantic_coverage=semantic_path,
            selector_run=None,
            failure_class=["declined_cannot_prove"],
            unit_key=None,
            output=output,
        )
    )

    task = json.loads((output / "tasks/unit-001.json").read_text(encoding="utf-8"))
    task_text = (output / "tasks/unit-001.md").read_text(encoding="utf-8")
    all_text = json.dumps(task, ensure_ascii=False) + task_text

    assert summary["unit_keys"] == ["unit-001"]
    assert task["source_unit"]["source_text"].startswith("\\begin{lemma}")
    assert task["visible_prompt_context"]["planned_declarations"][0]["hydrated_mathlib_context"][0]["exact_identifier"] == "Nat.add_zero"
    assert task["verification"]["visible_support_context"]["accepted"][0]["name"] == "Demo.visible"
    assert task["semantic_coverage"] == {
        "unit_key": "unit-001",
        "source_unit_id": "source:demo",
        "compile_passed": False,
        "coverage_status": "generated_not_compiled",
        "compile_gate_bypassed": None,
    }
    assert "Demo.hidden_gold" not in all_text
    assert "posthoc_lean_alignment" not in all_text
    assert "aligned_gold_declaration_count" not in all_text
    assert "semantic_passed_gold_declarations" not in all_text
    assert "checks" not in task["semantic_coverage"]


def test_builds_task_from_prior_proof_lane_payload(tmp_path: Path) -> None:
    selector = tmp_path / "selector"
    generation = tmp_path / "generation"
    output = tmp_path / "proof-lane"
    (selector / "eval").mkdir(parents=True)
    (generation / "batch-001").mkdir(parents=True)
    (generation / "eval").mkdir()

    selected = {
        "id": "source:demo",
        "source_unit": {
            "environment": "lemma",
            "path": "Demo.tex",
            "line_range": [1, 2],
            "labels": ["demo"],
            "referenced_labels": [],
            "part_markers": [],
            "parse_warnings": [],
            "source_text": "\\begin{lemma}\\label{demo}Demo source.\\end{lemma}",
        },
    }
    (selector / "eval/selected-units.jsonl").write_text(json.dumps(selected) + "\n", encoding="utf-8")
    (generation / "eval/generation-results.json").write_text(
        json.dumps({"selector_run": str(selector)}),
        encoding="utf-8",
    )
    (generation / "batch-001/generation-output.json").write_text(
        json.dumps(
            {
                "units": [
                    {
                        "unit_key": "unit-001",
                        "status": "cannot_prove_from_visible_context",
                        "lean_file_body": "",
                        "declaration_names": [],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    prior_task = {
        "unit_key": "unit-001",
        "visible_prompt_context": {
            "source_focus_summary": "preserved focus",
            "planned_declarations": [
                {
                    "task_id": "unit-001-task-1",
                    "kind": "lemma",
                    "role": "main_claim",
                    "hydrated_mathlib_context": [
                        {
                            "exact_identifier": "Nat.mul_one",
                            "lean_check": {"status": "checked", "signature": "Nat.mul_one ..."},
                        }
                    ],
                }
            ],
        },
    }
    (generation / "batch-001/generation-payload.json").write_text(
        json.dumps({"messages": [{"role": "user", "content": json.dumps({"proof_lane_tasks": [prior_task]})}]}),
        encoding="utf-8",
    )
    verification_path = generation / "eval/verification-results.json"
    verification_path.write_text(
        json.dumps(
            {
                "batches": [
                    {
                        "units": [
                            {
                                "unit_key": "unit-001",
                                "compile_passed": False,
                                "failure_class": "declined_cannot_prove",
                                "reported_status": "cannot_prove_from_visible_context",
                                "skipped_reason": "cannot_prove_from_visible_context",
                            }
                        ]
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    run(
        argparse.Namespace(
            generation_run=generation,
            verification_results=verification_path,
            semantic_coverage=None,
            selector_run=None,
            failure_class=["declined_cannot_prove"],
            unit_key=None,
            output=output,
        )
    )

    task = json.loads((output / "tasks/unit-001.json").read_text(encoding="utf-8"))

    assert task["visible_prompt_context"]["source_focus_summary"] == "preserved focus"
    assert (
        task["visible_prompt_context"]["planned_declarations"][0]["hydrated_mathlib_context"][0]["exact_identifier"]
        == "Nat.mul_one"
    )
