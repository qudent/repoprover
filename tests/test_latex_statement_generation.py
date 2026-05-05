"""Tests for theorem-level generation prompt assembly."""

import json
import argparse
from pathlib import Path

from scripts.run_latex_statement_generation import build_generation_messages, run


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
    assert "Follow the Lean-checked signatures exactly" in prompt
    assert "selector_unchecked_statement_sketch" in prompt
    assert "do not copy its Lean syntax verbatim" in prompt
    assert "cannot_prove_from_visible_context" in prompt
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
