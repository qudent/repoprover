"""Tests for theorem-level generation prompt assembly."""

import json
import argparse
from pathlib import Path

from scripts.run_latex_statement_generation import build_generation_messages, enforce_generation_contracts, run


def _write_selector_run(tmp_path: Path) -> Path:
    run_dir = tmp_path / "selector"
    (run_dir / "batch-001").mkdir(parents=True)
    (run_dir / "eval").mkdir()
    selected_unit = {
        "id": "source:demo.label",
        "source_unit": {
            "environment": "lemma",
            "path": "Demo.tex",
            "line_range": [1, 3],
            "labels": ["demo.label"],
            "referenced_labels": [],
            "part_markers": [],
            "parse_warnings": [],
            "source_text": "\\begin{lemma}\\label{demo.label}For all n, n + 0 = n.\\end{lemma}",
        },
        "posthoc_lean_alignment": {
            "aligned_lean_declarations": [
                {"full_name": "Demo.hidden_target", "name": "hidden_target"}
            ]
        },
    }
    (run_dir / "eval/selected-units.jsonl").write_text(json.dumps(selected_unit) + "\n", encoding="utf-8")
    (run_dir / "batch-001/context-selection-output.json").write_text(
        json.dumps(
            {
                "units": [
                    {
                        "unit_key": "unit-001",
                        "source_focus_summary": "addition by zero",
                        "formalization_risks": [],
                        "planned_declarations": [
                            {
                                "task_id": "unit-001-task-1",
                                "kind": "theorem",
                                "source_part": "whole unit",
                                "target_statement_sketch": "forall n, n + 0 = n",
                                "needed_source_context": ["demo.label"],
                                "needed_project_context": [],
                                "missing_or_uncertain_context": [],
                            }
                        ],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    (run_dir / "batch-001/context-selection-payload.json").write_text(
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
                                        "previous_source_context": [
                                            {"source_unit": {"id": "source:prior", "source_text": "Prior definition."}}
                                        ],
                                        "local_file_context_candidates": [
                                            {
                                                "kind": "variable",
                                                "name": "variable {K : Type*} [CommRing K]",
                                                "source": "file_context_from_prior_project_declaration",
                                            }
                                        ],
                                        "local_file_predecessor_declarations": [
                                            {
                                                "name": "Demo.prior_helper",
                                                "kind": "theorem",
                                                "lean_snippet": (
                                                    "/-- Do not leak Demo.hidden_target from comments. -/\n"
                                                    "theorem prior_helper (n : Nat) : n + 0 = n"
                                                ),
                                                "context_source": "same_file_before_selected_unit_line",
                                            }
                                        ],
                                        "prior_project_context": [
                                            {
                                                "source_unit_id": "source:prior",
                                                "project_declarations": [
                                                    {
                                                        "name": "Demo.PriorPredicate",
                                                        "kind": "def",
                                                        "lean_snippet": (
                                                            "-- target-shaped comment: Demo.hidden_target\n"
                                                            "def PriorPredicate (n : Nat) : Prop := n + 0 = n"
                                                        ),
                                                    }
                                                ],
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
    (run_dir / "batch-001/mathlib-lean-hydrated-context.json").write_text(
        json.dumps(
            {
                "opens": [],
                "hydrated_mathlib_context": [
                    {
                        "unit_key": "unit-001",
                        "task_id": "unit-001-task-1",
                        "query": "Nat.add_zero",
                        "exact_identifier": "Nat.add_zero",
                        "lean_check": {
                            "status": "checked",
                            "signature": "Nat.add_zero (n : Nat) : n + 0 = n",
                        },
                    },
                    {
                        "unit_key": "unit-001",
                        "task_id": "unit-001-task-1",
                        "query": "Demo.bad_guess",
                        "exact_identifier": "Demo.bad_guess",
                        "lean_check": {"status": "error", "error": "Unknown constant `Demo.bad_guess`"},
                        "fallback_mathlib_candidates": [{"name": "Demo.nearby"}],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return run_dir


def test_generation_prompt_uses_hydration_and_hides_posthoc_alignment(tmp_path: Path) -> None:
    run_dir = _write_selector_run(tmp_path)

    messages = build_generation_messages(run_dir)
    prompt = json.dumps(messages, ensure_ascii=False)

    assert "For all n" in prompt
    assert "Nat.add_zero (n : Nat)" in prompt
    assert "PriorPredicate" in prompt
    assert "target-shaped comment" not in prompt
    assert "available_prior_project_context" in prompt
    assert "previous_source_context" in prompt
    assert "local_file_context_candidates" in prompt
    assert "local_file_predecessor_declarations" in prompt
    assert "prior_helper" in prompt
    assert "variable {K : Type*} [CommRing K]" in prompt
    assert "Follow the Lean-checked signatures exactly" in prompt
    assert "Never use a hydrated Mathlib exact_identifier whose lean_check.status is not `checked`" in prompt
    assert "exact_identifier_failed_lean_check_redacted_do_not_use" in prompt
    assert "Demo.bad_guess" not in prompt
    assert "<redacted failed exact identifier>" in prompt
    assert "Every identifier used in a theorem statement must be introduced" in prompt
    assert "you may include the needed commands in lean_file_body" in prompt
    assert "you may reuse those exact helper names" in prompt
    assert "selector_unchecked_statement_sketch" in prompt
    assert "do not copy its Lean syntax verbatim" in prompt
    assert "cannot_prove_from_visible_context" in prompt
    assert "exactly empty string" in prompt
    assert "empty list when status is cannot_prove_from_visible_context" in prompt
    assert "do not use lean_file_body as a scratchpad" in prompt
    assert "Demo.hidden_target" not in prompt
    assert "posthoc_lean_alignment" not in prompt


def test_generation_budget_payload_disables_reasoning(tmp_path: Path) -> None:
    run_dir = _write_selector_run(tmp_path)
    output = tmp_path / "generation"

    summary = run(
        argparse.Namespace(
            selector_run=run_dir,
            output=output,
            model="deepseek/deepseek-v4-flash",
            base_url="https://openrouter.ai/api/v1",
            max_tokens=256,
            temperature=0.0,
            reasoning_effort="none",
            budget_only=True,
        )
    )

    assert summary["paid_call_made"] is False
    payload = json.loads((output / "batch-001/generation-payload.json").read_text(encoding="utf-8"))
    assert payload["extra_body"] == {"reasoning": {"effort": "none", "exclude": True}}


def test_enforce_generation_contracts_preserves_raw_needed_data() -> None:
    raw = {
        "units": [
            {
                "unit_key": "unit-001",
                "status": "cannot_prove_from_visible_context",
                "lean_file_body": "theorem scratch : True := by\n  sorry",
                "declaration_names": ["scratch"],
            },
            {
                "unit_key": "unit-002",
                "status": "generated",
                "lean_file_body": "theorem ok : True := by\n  trivial",
                "declaration_names": ["ok"],
            },
        ]
    }

    normalized, report = enforce_generation_contracts(raw)

    assert report["normalized_unit_count"] == 1
    assert normalized["units"][0]["lean_file_body"] == ""
    assert normalized["units"][0]["declaration_names"] == []
    assert normalized["units"][1]["declaration_names"] == ["ok"]
    assert raw["units"][0]["lean_file_body"].startswith("theorem scratch")
    assert "contract_enforcement" in normalized


def test_generation_budget_payload_can_split_units(tmp_path: Path) -> None:
    run_dir = _write_selector_run(tmp_path)
    selected_path = run_dir / "eval/selected-units.jsonl"
    first_selected = json.loads(selected_path.read_text(encoding="utf-8").strip())
    second_selected = dict(first_selected)
    second_selected["id"] = "source:demo.second"
    second_selected["source_unit"] = dict(first_selected["source_unit"], labels=["demo.second"])
    selected_path.write_text(
        "\n".join(json.dumps(row) for row in [first_selected, second_selected]) + "\n",
        encoding="utf-8",
    )
    selector_output_path = run_dir / "batch-001/context-selection-output.json"
    selector_output = json.loads(selector_output_path.read_text(encoding="utf-8"))
    second_unit = dict(selector_output["units"][0], unit_key="unit-002")
    second_unit["planned_declarations"] = [
        dict(task, task_id=str(task["task_id"]).replace("unit-001", "unit-002"))
        for task in selector_output["units"][0]["planned_declarations"]
    ]
    selector_output["units"].append(second_unit)
    selector_output_path.write_text(json.dumps(selector_output), encoding="utf-8")

    output = tmp_path / "generation"
    summary = run(
        argparse.Namespace(
            selector_run=run_dir,
            output=output,
            model="deepseek/deepseek-v4-flash",
            base_url="https://openrouter.ai/api/v1",
            max_tokens=256,
            max_units_per_call=1,
            temperature=0.0,
            reasoning_effort="none",
            budget_only=True,
        )
    )

    assert summary["batch_count"] == 2
    assert (output / "batch-001/generation-payload.json").exists()
    assert (output / "batch-002/generation-payload.json").exists()
    payload_1 = json.loads((output / "batch-001/generation-payload.json").read_text(encoding="utf-8"))
    payload_2 = json.loads((output / "batch-002/generation-payload.json").read_text(encoding="utf-8"))
    assert '"unit_key": "unit-001"' in payload_1["messages"][1]["content"]
    assert '"unit_key": "unit-002"' not in payload_1["messages"][1]["content"]
    assert '"unit_key": "unit-002"' in payload_2["messages"][1]["content"]


def test_generation_budget_payload_can_filter_unit_keys(tmp_path: Path) -> None:
    run_dir = _write_selector_run(tmp_path)
    selected_path = run_dir / "eval/selected-units.jsonl"
    first_selected = json.loads(selected_path.read_text(encoding="utf-8").strip())
    second_selected = dict(first_selected)
    second_selected["id"] = "source:demo.second"
    selected_path.write_text(
        "\n".join(json.dumps(row) for row in [first_selected, second_selected]) + "\n",
        encoding="utf-8",
    )
    selector_output_path = run_dir / "batch-001/context-selection-output.json"
    selector_output = json.loads(selector_output_path.read_text(encoding="utf-8"))
    selector_output["units"].append(dict(selector_output["units"][0], unit_key="unit-002"))
    selector_output_path.write_text(json.dumps(selector_output), encoding="utf-8")

    output = tmp_path / "generation"
    summary = run(
        argparse.Namespace(
            selector_run=run_dir,
            output=output,
            unit_key=["unit-002"],
            model="deepseek/deepseek-v4-flash",
            base_url="https://openrouter.ai/api/v1",
            max_tokens=256,
            max_units_per_call=1,
            temperature=0.0,
            reasoning_effort="none",
            budget_only=True,
        )
    )

    assert summary["batch_count"] == 1
    payload = json.loads((output / "batch-001/generation-payload.json").read_text(encoding="utf-8"))
    user_payload = json.loads(payload["messages"][1]["content"])
    assert [unit["unit_key"] for unit in user_payload["units"]] == ["unit-002"]
