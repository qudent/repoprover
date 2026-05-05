"""Tests for theorem-level context-selection payloads."""

from scripts.run_latex_statement_context_selection import SelectedUnit, build_messages


def _unit(
    *,
    unit_id: str,
    label: str,
    source_text: str,
    aligned_name: str | None = None,
    refs: list[dict] | None = None,
) -> dict:
    row = {
        "id": unit_id,
        "source_unit": {
            "environment": "lemma",
            "path": "AlgebraicCombinatorics/tex/Demo.tex",
            "line_range": [1, 3],
            "labels": [label],
            "referenced_labels": [],
            "part_markers": [],
            "source_text": source_text,
            "parse_warnings": [],
        },
        "context_candidates": {
            "referenced_source_units": refs or [],
            "previous_same_file_source_units": [],
        },
        "posthoc_lean_alignment": {
            "aligned_lean_declarations": [],
        },
        "selection": {"status": "gold_candidate"},
    }
    if aligned_name:
        row["posthoc_lean_alignment"]["aligned_lean_declarations"].append(
            {
                "full_name": aligned_name,
                "kind": "theorem",
                "path": "AlgebraicCombinatorics/Demo.lean",
                "line_range": [10, 12],
                "declared_source_labels": [label],
            }
        )
    return row


def test_theorem_level_selector_hides_target_alignment_but_keeps_prior_context() -> None:
    prior = _unit(
        unit_id="prior",
        label="lem.prior",
        source_text="\\begin{lemma}\\label{lem.prior}Prior.\\end{lemma}",
        aligned_name="Demo.prior_theorem",
    )
    target = _unit(
        unit_id="target",
        label="lem.target",
        source_text="\\begin{lemma}\\label{lem.target}Target uses \\ref{lem.prior}.\\end{lemma}",
        aligned_name="Demo.hidden_target",
        refs=[{"unit_id": "prior", "label": "lem.prior", "resolved": True}],
    )

    messages = build_messages([SelectedUnit(public_key="unit-001", row=target)], [prior, target])
    prompt = messages[1]["content"]

    assert "Target uses" in prompt
    assert "Demo.prior_theorem" in prompt
    assert "Demo.hidden_target" not in prompt
    assert "posthoc_lean_alignment" not in prompt
    assert "needed_mathlib_context" in prompt
    assert "prior_project_context" in prompt
