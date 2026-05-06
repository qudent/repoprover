"""Tests for theorem-level generation repair prompt assembly."""

import argparse
import json
from pathlib import Path

from scripts.run_latex_statement_generation_repair import build_repair_messages, run


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
                                                "name": "Demo.prior_helper",
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
        json.dumps(
            {
                "opens": [],
                "hydrated_mathlib_context": [
                    {
                        "unit_key": "unit-001",
                        "task_id": "unit-001-task-1",
                        "query": "Demo.bad_guess",
                        "exact_identifier": "Demo.bad_guess",
                        "lean_check": {"status": "error", "error": "Unknown constant `Demo.bad_guess`"},
                    }
                ],
            }
        ),
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


def test_repair_prompt_includes_errors_and_hides_posthoc_alignment(tmp_path: Path) -> None:
    selector_run, generation_run, verification_path = _write_failed_run(tmp_path)
    extra_context = tmp_path / "extra.json"
    extra_context.write_text(
        json.dumps(
            {
                "checked_signatures": [{"name": "Nat.add_zero", "signature": "n + 0 = n"}],
                "discarded_do_not_use_items": [
                    {"unit_key": "unit-001", "item": "Nat.add_zero as a rewrite"}
                ],
                "same_unit_helper_plan": [
                    {
                        "unit_key": "unit-001",
                        "role": "lemma",
                        "fresh_name_hint": "helper_add_zero",
                        "statement_sketch": "helper theorem about n + 0",
                    }
                ],
                "fallback_bridge_notes": [
                    {
                        "bridge_kind": "multiset_sort_sum_preservation",
                        "proof_guidance": "Use checked fallback rewrite chain.",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    messages = build_repair_messages(
        selector_run=selector_run,
        generation_run=generation_run,
        verification_results=verification_path,
        extra_context_paths=[extra_context],
    )
    prompt = json.dumps(messages, ensure_ascii=False)

    assert "Unknown constant `Demo.bad_guess`" in prompt
    assert "Do not use any identifier that Lean already reported as Unknown constant" in prompt
    assert "attempt that checked route before declaring cannot_prove_from_visible_context" in prompt
    assert "implement that proof in lean_file_body" in prompt
    assert "do not use lean_file_body as a scratchpad" in prompt
    assert "prior_helper" in prompt
    assert "Nat.add_zero" in prompt
    assert "same_unit_helper_plan" in prompt
    assert "helper_add_zero" in prompt
    assert "newly introduced declarations" in prompt
    assert "Do not introduce a replacement carrier type" in prompt
    assert "checked sort/enumeration route can be a valid local helper plan" in prompt
    assert "direct library theorem for the whole padded function is not required" in prompt
    assert "padded definition, in-range get lemma" in prompt
    assert "fallback_resolved_context_requests" in prompt
    assert "fallback_bridge_notes" in prompt
    assert "generic checked-fallback rewrite/application routes" in prompt
    assert "schema sanitation notes only" in prompt
    assert "theorem bad" in prompt
    assert "Demo.hidden_target" not in prompt
    assert "posthoc_lean_alignment" not in prompt


def test_repair_prompt_includes_raw_invalid_generation_output_as_unchecked(tmp_path: Path) -> None:
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

    messages = build_repair_messages(
        selector_run=selector_run,
        generation_run=generation_run,
        verification_results=verification_path,
    )
    prompt = json.dumps(messages, ensure_ascii=False)

    assert "raw_invalid_generation_output" in prompt
    assert "unverified prior scratchpad only" in prompt
    assert "theorem scratch" in prompt
    assert "Demo.hidden_target" not in prompt


def test_repair_budget_payload_writes_generation_payload(tmp_path: Path) -> None:
    selector_run, generation_run, verification_path = _write_failed_run(tmp_path)
    output = tmp_path / "repair"

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
            extra_context=None,
            budget_only=True,
        )
    )

    assert summary["paid_call_made"] is False
    assert (output / "batch-001/generation-payload.json").exists()
    assert (output / "batch-001/repair-payload.json").exists()
