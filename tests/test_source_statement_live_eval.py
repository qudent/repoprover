"""Tests for target-statement-withheld source-statement eval prompts."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.materialize_minimal_context_smoke import SelectedRecord
from scripts.run_source_statement_live_eval import build_messages


def _write_fixture_project(tmp_path: Path) -> tuple[Path, SelectedRecord]:
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "Demo.lean").write_text(
        "\n".join(
            [
                "import Mathlib",
                "open scoped Matrix BigOperators",
                "open Finset Matrix",
                "",
                "namespace Demo",
                "",
                "variable {R : Type*} [CommRing R]",
                "",
                "/-- The submatrix helper used by the local notation. -/",
                "noncomputable def submatrixOfFinset {n m : Nat} (A : Matrix (Fin n) (Fin m) R)",
                "    (U : Finset (Fin n)) (V : Finset (Fin m)) :",
                "    Matrix (Fin U.card) (Fin V.card) R :=",
                "  A.submatrix (U.orderEmbOfFin rfl) (V.orderEmbOfFin rfl)",
                "",
                "/-- Notation for submatrices: `sub[U,V] A` denotes sub_U^V A. -/",
                'scoped notation "sub[" U "," V "] " A => submatrixOfFinset A U V',
                "",
                "/-- Local style example: use Mathlib's `.submatrix` API for diagonal principal minors. -/",
                "example {n : Nat} (d : Fin n -> R) (P : Finset (Fin n)) :",
                "    ((Matrix.diagonal d).submatrix (P.orderEmbOfFin rfl) (P.orderEmbOfFin rfl)).det =",
                "    ∏ i ∈ P, d i := by",
                "  sorry",
                "",
                "/-- Part (a): target declaration withheld in prompts.",
                "    Label: demo.minors.a -/",
                "theorem target {n : Nat} (d : Fin n -> R) (P : Finset (Fin n)) : True := by",
                "  trivial",
                "",
                "end Demo",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (project_root / "Demo.tex").write_text(
        "\\begin{lemma}\\label{demo.minors} Then: "
        "\\textbf{(a)} principal minors are products. "
        "\\textbf{(b)} off-diagonal minors vanish.\\end{lemma}\n",
        encoding="utf-8",
    )
    row = {
        "id": "Demo.lean:Demo.target",
        "alignment": {
            "comment_labels": ["demo.minors", "demo.minors.a"],
            "paired_source_path": "Demo.tex",
            "source_method": "lean_comment_label",
        },
        "output": {
            "lean_path": "Demo.lean",
            "declaration_names": ["Demo.target"],
            "line_range": [24, 26],
            "chunk_kind": "theorem",
        },
        "minimal_context": {
            "source_spans": [{"path": "Demo.tex", "line_range": [1, 1], "labels": ["demo.minors"]}],
            "file_context": [
                {"path": "Demo.lean", "kind": "open", "line_range": [2, 2], "name": "open scoped Matrix BigOperators"},
                {"path": "Demo.lean", "kind": "open", "line_range": [3, 3], "name": "open Finset Matrix"},
                {"path": "Demo.lean", "kind": "namespace", "line_range": [5, 5], "name": "Demo"},
                {"path": "Demo.lean", "kind": "variable", "line_range": [7, 7], "name": "variable {R : Type*} [CommRing R]"},
                {
                    "path": "Demo.lean",
                    "kind": "notation",
                    "line_range": [16, 16],
                    "name": 'scoped notation "sub[" U "," V "] " A => submatrixOfFinset A U V',
                },
            ],
            "lean_predecessors": [],
            "mathlib_context": ["Mathlib context"],
        },
    }
    return project_root, SelectedRecord(row)


def test_source_statement_prompt_includes_local_style_and_notation_contract(tmp_path: Path) -> None:
    project_root, record = _write_fixture_project(tmp_path)

    messages = build_messages(project_root, record)
    user = json.loads(messages[1]["content"])
    context = user["context"]
    local_style = context["local_lean_style"]
    guide = "\n".join(local_style["guidance"])
    examples = "\n".join(local_style["examples"])

    assert "sub[U,V] A" in guide
    assert "submatrixOfFinset A U V" in guide
    assert "do not cite or invent raw helper names" in guide
    assert "scoped notation" in examples
    assert "noncomputable def submatrixOfFinset" in examples
    assert "((Matrix.diagonal d).submatrix" in examples


def test_source_statement_prompt_focuses_specific_part_of_multipart_source(tmp_path: Path) -> None:
    project_root, record = _write_fixture_project(tmp_path)

    messages = build_messages(project_root, record)
    user = json.loads(messages[1]["content"])
    instructions = "\n".join(user["instructions"])
    focus = user["context"]["target_source_focus"]

    assert focus["specific_source_labels"] == ["demo.minors.a"]
    assert focus["specific_labeled_parts"] == ["a"]
    assert "formalize only the specified labeled part/source span" in instructions
    assert "Do not conjoin all parts" in instructions
