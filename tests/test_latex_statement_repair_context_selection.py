"""Tests for theorem-level repair-context selection."""

import argparse
import json
from pathlib import Path

from scripts.build_latex_statement_repair_context_pack import build_context_pack
from scripts.run_latex_statement_repair_context_selection import (
    build_hydratable_selector_output,
    build_repair_context_messages,
    run,
)


def _write_failed_run(tmp_path: Path) -> tuple[Path, Path, Path]:
    selector_run = tmp_path / "selector"
    generation_run = tmp_path / "generation"
    (selector_run / "batch-001").mkdir(parents=True)
    (selector_run / "eval").mkdir()
    (generation_run / "batch-001").mkdir(parents=True)
    (generation_run / "eval").mkdir()

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
            "aligned_lean_declarations": [{"full_name": "Demo.hidden_target", "name": "hidden_target"}]
        },
    }
    (selector_run / "eval/selected-units.jsonl").write_text(json.dumps(selected_unit) + "\n", encoding="utf-8")
    (selector_run / "batch-001/context-selection-output.json").write_text(
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
    (selector_run / "batch-001/context-selection-payload.json").write_text(
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
                                        "previous_source_context": [],
                                        "local_file_context_candidates": [],
                                        "local_file_predecessor_declarations": [
                                            {
                                                "name": "prior_helper",
                                                "kind": "theorem",
                                                "lean_snippet": "theorem prior_helper (n : Nat) : n + 0 = n",
                                            }
                                        ],
                                        "prior_project_context": [],
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
    (selector_run / "batch-001/mathlib-lean-hydrated-context.json").write_text(
        json.dumps({"opens": [], "hydrated_mathlib_context": []}),
        encoding="utf-8",
    )
    (generation_run / "batch-001/generation-output.json").write_text(
        json.dumps(
            {
                "units": [
                    {
                        "unit_key": "unit-001",
                        "status": "generated",
                        "declaration_names": ["bad"],
                        "lean_file_body": "theorem bad : True := by\n  exact Demo.bad_guess",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    verification_path = generation_run / "eval/verification-results.json"
    verification_path.write_text(
        json.dumps(
            {
                "compile_passed_units": 0,
                "unit_count": 1,
                "batches": [
                    {
                        "units": [
                            {
                                "unit_key": "unit-001",
                                "compile_passed": False,
                                "messages": [
                                    {
                                        "severity": "error",
                                        "data": "Unknown constant `Demo.bad_guess`",
                                    }
                                ],
                            }
                        ]
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return selector_run, generation_run, verification_path


def test_repair_context_prompt_selects_context_without_hidden_target(tmp_path: Path) -> None:
    selector_run, generation_run, verification_path = _write_failed_run(tmp_path)

    messages = build_repair_context_messages(
        selector_run=selector_run,
        generation_run=generation_run,
        verification_results=verification_path,
    )
    prompt = json.dumps(messages, ensure_ascii=False)

    assert "Unknown constant `Demo.bad_guess`" in prompt
    assert "Do not output Lean theorem code" in prompt
    assert "Do not stop at a missing direct theorem" in prompt
    assert "same_unit_helper_plan" in prompt
    assert "fresh descriptive names" in prompt
    assert "do_not_use_identifiers must contain exact Lean identifiers only" in prompt
    assert "request the checked pointwise/application lemmas" in prompt
    assert "Multiset.card_map" in prompt
    assert "prior_helper" in prompt
    assert "Demo.hidden_target" not in prompt
    assert "posthoc_lean_alignment" not in prompt


def test_repair_context_prompt_includes_previous_checked_repair_context(tmp_path: Path) -> None:
    selector_run, generation_run, verification_path = _write_failed_run(tmp_path)
    (generation_run / "batch-001/repair-payload.json").write_text(
        json.dumps(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": json.dumps(
                            {
                                "additional_checked_repair_context": [
                                    {
                                        "checked_signatures": [
                                            {"name": "Finset.sum_empty", "signature": "sum over empty is zero"}
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

    messages = build_repair_context_messages(
        selector_run=selector_run,
        generation_run=generation_run,
        verification_results=verification_path,
    )
    prompt = json.dumps(messages, ensure_ascii=False)

    assert "previous_checked_repair_context" in prompt
    assert "Finset.sum_empty" in prompt


def test_repair_context_prompt_includes_source_coverage_review_keys(tmp_path: Path) -> None:
    selector_run, generation_run, verification_path = _write_failed_run(tmp_path)

    messages = build_repair_context_messages(
        selector_run=selector_run,
        generation_run=generation_run,
        verification_results=verification_path,
        source_coverage_review_unit_keys=["unit-001"],
    )
    prompt = json.dumps(messages, ensure_ascii=False)
    user_payload = json.loads(messages[1]["content"])

    assert user_payload["source_coverage_review_unit_keys"] == ["unit-001"]
    assert "review the visible source text against the generated declarations" in prompt
    assert "does not include gold declarations" not in prompt


def test_repair_context_prompt_includes_raw_invalid_generation_output_as_unchecked(tmp_path: Path) -> None:
    selector_run, generation_run, verification_path = _write_failed_run(tmp_path)
    (generation_run / "batch-001/raw-generation-output.json").write_text(
        json.dumps(
            {
                "units": [
                    {
                        "unit_key": "unit-001",
                        "status": "cannot_prove_from_visible_context",
                        "declaration_names": ["scratch"],
                        "lean_file_body": "theorem scratch : True := by\n  trivial",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    messages = build_repair_context_messages(
        selector_run=selector_run,
        generation_run=generation_run,
        verification_results=verification_path,
    )
    prompt = json.dumps(messages, ensure_ascii=False)

    assert "raw_invalid_generation_output" in prompt
    assert "unverified prior scratchpad only" in prompt
    assert "theorem scratch" in prompt
    assert "Demo.hidden_target" not in prompt


def test_hydratable_selector_output_keeps_only_mathlib_requests() -> None:
    selection = {
        "units": [
            {
                "unit_key": "unit-001",
                "selected_visible_context": [{"name_or_label": "prior_helper"}],
                "needed_mathlib_context": [
                    {
                        "name_or_query": "Nat.add_zero",
                        "expected_signature_or_shape": "n + 0 = n",
                        "why_needed": "close the proof",
                    }
                ],
            }
        ]
    }

    hydratable = build_hydratable_selector_output(selection)

    task = hydratable["units"][0]["planned_declarations"][0]
    assert task["task_id"] == "unit-001-repair-context-1"
    assert task["needed_mathlib_context"][0]["name_or_query"] == "Nat.add_zero"
    assert "selected_visible_context" not in json.dumps(hydratable)


def test_checked_context_pack_records_hydrated_signatures() -> None:
    selection = {
        "units": [
            {
                "unit_key": "unit-001",
                "failure_analysis": "bad theorem name",
                "repair_strategy_note": "rewrite with visible helper, then use add_zero",
                "selected_visible_context": [
                    {
                        "context_kind": "local_file_predecessor",
                        "name_or_label": "prior_helper",
                        "why_needed": "rewrite the target",
                    }
                ],
                "same_unit_helper_plan": [
                    {
                        "role": "lemma",
                        "fresh_name_hint": "prior_helper_zero",
                        "statement_sketch": "a helper lemma about adding zero",
                        "depends_on": ["prior_helper"],
                        "needed_checked_ingredients": ["Nat.add_zero"],
                        "why_needed": "main proof closes by this helper",
                    }
                ],
                "needed_mathlib_context": [
                    {
                        "name_or_query": "Nat.add_zero",
                        "expected_signature_or_shape": "n + 0 = n",
                        "why_needed": "close the proof",
                    }
                ],
                "do_not_use_identifiers": ["Demo.bad_guess", "Demo.bad_guess as a rewrite"],
                "missing_or_uncertain_context": [],
                "selector_confidence": 0.8,
            }
        ]
    }
    hydration = {
        "hydrated_mathlib_context": [
            {
                "unit_key": "unit-001",
                "task_id": "unit-001-repair-context-1",
                "request_index": 1,
                "query": "Nat.add_zero",
                "exact_identifier": "Nat.add_zero",
                "expected_signature_or_shape": "n + 0 = n",
                "why_needed": "close the proof",
                "lean_check": {"status": "checked", "signature": "Nat.add_zero (n : Nat) : n + 0 = n"},
                "related_mathlib_declarations": [
                    {
                        "name": "Nat.add_zero_related",
                        "lean_check": {"status": "checked", "signature": "Nat.add_zero_related : True"},
                    }
                ],
            }
        ]
    }

    pack = build_context_pack(selection=selection, hydration=hydration)

    assert pack["checked_signatures"][0]["name"] == "Nat.add_zero"
    assert pack["checked_signatures"][1]["name"] == "Nat.add_zero_related"
    assert pack["checked_signatures"][1]["related_to"] == "Nat.add_zero"
    assert pack["proof_strategy_notes"][0]["proof_strategy_note"] == "rewrite with visible helper, then use add_zero"
    assert pack["same_unit_helper_plan"][0]["fresh_name_hint"] == "prior_helper_zero"
    assert pack["selected_visible_context"][0]["name_or_label"] == "prior_helper"
    assert pack["do_not_use_identifiers"] == ["Demo.bad_guess"]
    assert pack["discarded_do_not_use_items"] == [
        {
            "unit_key": "unit-001",
            "item": "Demo.bad_guess as a rewrite",
            "reason": "not_an_exact_lean_identifier",
        }
    ]


def test_checked_context_pack_promotes_checked_fallback_candidates() -> None:
    selection = {
        "units": [
            {
                "unit_key": "unit-001",
                "failure_analysis": "bad theorem name",
                "repair_strategy_note": "use an emptiness iff fallback",
                "needed_mathlib_context": [
                    {
                        "name_or_query": "Finset.powersetCard_eq_empty_of_lt",
                        "why_needed": "show the index set is empty",
                    }
                ],
            }
        ]
    }
    hydration = {
        "hydrated_mathlib_context": [
            {
                "unit_key": "unit-001",
                "task_id": "unit-001-repair-context-1",
                "request_index": 1,
                "query": "Finset.powersetCard_eq_empty_of_lt",
                "exact_identifier": "Finset.powersetCard_eq_empty_of_lt",
                "why_needed": "show the index set is empty",
                "lean_check": {"status": "error", "error": "Unknown constant"},
                "fallback_mathlib_candidates": [
                    {
                        "name": "Finset.powersetCard_eq_empty",
                        "declaration_line": "lemma powersetCard_eq_empty : powersetCard n s = ∅ ↔ s.card < n := by",
                        "lean_check": {
                            "status": "checked",
                            "signature": "Finset.powersetCard_eq_empty : powersetCard n s = ∅ ↔ s.card < n",
                        },
                    }
                ],
            }
        ]
    }

    pack = build_context_pack(selection=selection, hydration=hydration)

    assert pack["checked_signatures"][0]["name"] == "Finset.powersetCard_eq_empty"
    assert pack["checked_signatures"][0]["fallback_for_query"] == "Finset.powersetCard_eq_empty_of_lt"
    assert pack["failed_or_unchecked_context_requests"][0]["exact_identifier"] == "Finset.powersetCard_eq_empty_of_lt"


def test_repair_context_budget_payload(tmp_path: Path) -> None:
    selector_run, generation_run, verification_path = _write_failed_run(tmp_path)
    output = tmp_path / "repair-context"

    summary = run(
        argparse.Namespace(
            selector_run=selector_run,
            generation_run=generation_run,
            verification_results=verification_path,
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
    assert (output / "batch-001/repair-context-selection-payload.json").exists()
