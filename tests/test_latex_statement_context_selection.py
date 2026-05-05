"""Tests for theorem-level context-selection payloads."""

import json
from pathlib import Path

from scripts.run_latex_statement_context_selection import SelectedUnit, build_messages, select_units


def _unit(
    *,
    unit_id: str,
    label: str,
    source_text: str,
    aligned_name: str | None = None,
    referencing_name: str | None = None,
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
            "referencing_lean_declarations": [],
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
                "file_context": [
                    {
                        "path": "AlgebraicCombinatorics/Demo.lean",
                        "kind": "variable",
                        "name": "variable {K : Type*} [CommRing K]",
                        "line_range": [5, 5],
                    }
                ],
            }
        )
    if referencing_name:
        row["posthoc_lean_alignment"]["referencing_lean_declarations"].append(
            {
                "full_name": referencing_name,
                "kind": "def",
                "path": "AlgebraicCombinatorics/Demo.lean",
                "line_range": [20, 22],
                "declared_source_labels": [],
                "referenced_source_labels": [label],
                "file_context": [
                    {
                        "path": "AlgebraicCombinatorics/Demo.lean",
                        "kind": "namespace",
                        "name": "Demo",
                        "line_range": [4, 4],
                    }
                ],
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

    messages = build_messages([SelectedUnit(public_key="unit-001", row=target)], [prior, target], source_units=[prior, target])
    prompt = messages[1]["content"]

    assert "Target uses" in prompt
    assert "Prior." in prompt
    assert "Demo.prior_theorem" in prompt
    assert "Demo.hidden_target" not in prompt
    assert "posthoc_lean_alignment" not in prompt
    assert "needed_mathlib_context" in prompt
    assert "prior_project_context" in prompt
    assert "previous_source_context" in prompt
    assert "local_file_context_candidates" in prompt
    assert "variable {K : Type*} [CommRing K]" in prompt
    assert "Do not write theorem/lemma Lean code in target_statement_sketch" in prompt


def test_theorem_level_selector_uses_source_unit_only_referencing_declarations() -> None:
    prior = _unit(
        unit_id="prior-definition",
        label="def.prior",
        source_text="\\begin{definition}\\label{def.prior}Prior definition.\\end{definition}",
        referencing_name="Demo.PriorPredicate",
    )
    target = _unit(
        unit_id="target",
        label="thm.target",
        source_text="\\begin{theorem}\\label{thm.target}Target uses the prior definition.\\end{theorem}",
        aligned_name="Demo.hidden_target",
        refs=[{"unit_id": "prior-definition", "label": "def.prior", "resolved": True}],
    )

    messages = build_messages([SelectedUnit(public_key="unit-001", row=target)], [target], source_units=[prior, target])
    prompt = messages[1]["content"]

    assert "Demo.PriorPredicate" in prompt
    assert "referencing_prior_declaration" in prompt
    assert "local_file_context_candidates" in prompt
    assert "Demo.hidden_target" not in prompt


def test_prior_project_context_uses_compact_statements_and_file_context(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    lean_path = project_root / "AlgebraicCombinatorics/Demo.lean"
    lean_path.parent.mkdir(parents=True)
    lean_path.write_text(
        "\n".join(
            [
                "import Mathlib",
                "namespace Demo",
                "variable {K : Type*} [CommRing K]",
                "/-- Prior theorem. -/",
                "theorem prior_theorem (x : K) : x = x := by",
                "  rfl",
            ]
        ),
        encoding="utf-8",
    )
    prior = _unit(
        unit_id="prior",
        label="lem.prior",
        source_text="\\begin{lemma}\\label{lem.prior}Prior.\\end{lemma}",
        aligned_name="Demo.prior_theorem",
    )
    prior["posthoc_lean_alignment"]["aligned_lean_declarations"][0]["line_range"] = [4, 6]
    target = _unit(
        unit_id="target",
        label="lem.target",
        source_text="\\begin{lemma}\\label{lem.target}Target uses \\ref{lem.prior}.\\end{lemma}",
        aligned_name="Demo.hidden_target",
        refs=[{"unit_id": "prior", "label": "lem.prior", "resolved": True}],
    )

    messages = build_messages(
        [SelectedUnit(public_key="unit-001", row=target)],
        [prior, target],
        source_units=[prior, target],
        project_root=project_root,
    )
    payload = json.loads(messages[1]["content"])
    prior_decl = payload["units"][0]["prior_project_context"][0]["project_declarations"][0]

    assert prior_decl["lean_snippet"] == "/-- Prior theorem. -/\ntheorem prior_theorem (x : K) : x = x"
    assert "rfl" not in prior_decl["lean_snippet"]
    assert payload["units"][0]["local_file_context_candidates"][0]["kind"] == "variable"
    assert payload["units"][0]["local_file_context_candidates"][0]["name"] == "variable {K : Type*} [CommRing K]"


def test_select_units_supports_offset_and_exact_id() -> None:
    rows = [
        {**_unit(unit_id="u1", label="l1", source_text="one"), "selection": {"status": "gold_candidate"}},
        {**_unit(unit_id="u2", label="l2", source_text="two"), "selection": {"status": "gold_candidate"}},
    ]

    assert select_units(rows, 1, offset=1)[0].row["id"] == "u2"
    assert select_units(rows, 1, unit_id="u1")[0].row["id"] == "u1"


def test_context_selection_caps_same_file_predecessors() -> None:
    previous = [
        _unit(unit_id=f"prior-{index}", label=f"lem.prior{index}", source_text=f"Prior {index}")
        for index in range(3)
    ]
    target = _unit(
        unit_id="target",
        label="lem.target",
        source_text="\\begin{lemma}\\label{lem.target}Target.\\end{lemma}",
        refs=[],
    )
    target["context_candidates"]["previous_same_file_source_units"] = [
        {"unit_id": row["id"], "label": row["source_unit"]["labels"][0], "resolved": True} for row in previous
    ]

    messages = build_messages(
        [SelectedUnit(public_key="unit-001", row=target)],
        [*previous, target],
        source_units=[*previous, target],
        max_previous_same_file=2,
    )
    payload = json.loads(messages[1]["content"])
    selected_refs = payload["units"][0]["source_context_candidates"]["selected_context_refs"]

    assert [ref["unit_id"] for ref in selected_refs] == ["prior-1", "prior-2"]
    assert "Prior 0" not in messages[1]["content"]
    assert "Prior 1" in messages[1]["content"]
