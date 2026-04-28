"""Tests for static adversarial review of minimal-context gold candidates."""

from __future__ import annotations

from pathlib import Path

from scripts.adversarial_review_gold_candidates import (
    ProjectText,
    build_declaration_index,
    review_record,
)


def write_project(tmp_path: Path, lean_text: str, tex_text: str) -> None:
    lean_path = tmp_path / "AlgebraicCombinatorics" / "Toy.lean"
    tex_path = tmp_path / "AlgebraicCombinatorics" / "tex" / "Toy.tex"
    lean_path.parent.mkdir(parents=True)
    tex_path.parent.mkdir(parents=True)
    lean_path.write_text(lean_text, encoding="utf-8")
    tex_path.write_text(tex_text, encoding="utf-8")


def base_record() -> dict:
    return {
        "id": "AlgebraicCombinatorics/Toy.lean:Toy.target",
        "chapter_id": "toy",
        "output": {
            "lean_path": "AlgebraicCombinatorics/Toy.lean",
            "declaration_names": ["Toy.target"],
            "line_range": [2, 4],
            "chunk_kind": "theorem",
        },
        "minimal_context": {
            "source_spans": [
                {
                    "path": "AlgebraicCombinatorics/tex/Toy.tex",
                    "line_range": [1, 3],
                    "labels": ["thm.toy"],
                    "method": "lean_comment_label",
                    "reason": "Lean doc comment references this TeX label.",
                }
            ],
            "lean_predecessors": [],
            "imports": [],
            "import_closure": [],
            "mathlib_context": [],
        },
        "alignment": {
            "source_method": "lean_comment_label",
            "comment_labels": ["thm.toy"],
            "paired_source_path": "AlgebraicCombinatorics/tex/Toy.tex",
        },
        "trust": {
            "source_span": 0.75,
            "lean_dependency_graph": 0.25,
            "model_extraction": 0.0,
            "human_review": 0.0,
        },
        "review_notes": [],
        "generation": {"generator_version": "test", "generator_kind": "deterministic_static_analysis"},
    }


def review(tmp_path: Path, record: dict):
    return review_record(record, build_declaration_index(tmp_path), ProjectText(tmp_path))


def test_static_review_accepts_mechanically_consistent_record(tmp_path: Path) -> None:
    write_project(
        tmp_path,
        "\n".join(
            [
                "namespace Toy",
                "/-- Theorem \\ref{thm.toy}. -/",
                "theorem target : True := by",
                "  trivial",
                "end Toy",
            ]
        )
        + "\n",
        "\\label{thm.toy}\nStatement.\nProof.\n",
    )

    result = review(tmp_path, base_record())

    assert result.verdict == "provisionally_accept"
    assert result.label_or_line_issues == []


def test_static_review_rejects_missing_source_label(tmp_path: Path) -> None:
    write_project(
        tmp_path,
        "namespace Toy\n/-- Theorem \\ref{thm.toy}. -/\ntheorem target : True := by\n  trivial\nend Toy\n",
        "Statement without the label.\nMore text.\n",
    )

    result = review(tmp_path, base_record())

    assert result.verdict == "reject"
    assert any("does not contain" in issue for issue in result.label_or_line_issues)


def test_static_review_accepts_parent_source_label_for_subpart_comment(tmp_path: Path) -> None:
    write_project(
        tmp_path,
        "\n".join(
            [
                "namespace Toy",
                "/-- Theorem thm.toy (a). Label: thm.toy.a -/",
                "theorem target : True := by",
                "  trivial",
                "end Toy",
            ]
        )
        + "\n",
        "\\label{thm.toy}\nStatement with parts.\nProof.\n",
    )
    record = base_record()
    record["alignment"]["comment_labels"] = ["thm.toy", "thm.toy.a"]

    result = review(tmp_path, record)

    assert result.verdict == "provisionally_accept"
    assert result.missing_context == []


def test_static_review_ignores_sorry_inside_comments(tmp_path: Path) -> None:
    write_project(
        tmp_path,
        "\n".join(
            [
                "namespace Toy",
                "/-- This complete proof mentions a prior sorry in prose. Theorem \\ref{thm.toy}. -/",
                "theorem target : True := by",
                "  trivial",
                "end Toy",
            ]
        )
        + "\n",
        "\\label{thm.toy}\nStatement.\nProof.\n",
    )

    result = review(tmp_path, base_record())

    assert result.verdict == "provisionally_accept"
    assert not any("sorry" in issue for issue in result.label_or_line_issues)


def test_static_review_rejects_sorry_in_code(tmp_path: Path) -> None:
    write_project(
        tmp_path,
        "\n".join(
            [
                "namespace Toy",
                "/-- Theorem \\ref{thm.toy}. -/",
                "theorem target : True := by",
                "  sorry",
                "end Toy",
            ]
        )
        + "\n",
        "\\label{thm.toy}\nStatement.\nProof.\n",
    )

    result = review(tmp_path, base_record())

    assert result.verdict == "reject"
    assert any("sorry" in issue for issue in result.label_or_line_issues)


def test_static_review_rejects_future_predecessor(tmp_path: Path) -> None:
    write_project(
        tmp_path,
        "\n".join(
            [
                "namespace Toy",
                "/-- Theorem \\ref{thm.toy}. -/",
                "theorem target : True := by",
                "  trivial",
                "theorem futureHelper : True := by",
                "  trivial",
                "end Toy",
            ]
        )
        + "\n",
        "\\label{thm.toy}\nStatement.\nProof.\n",
    )
    record = base_record()
    record["minimal_context"]["lean_predecessors"] = [
        {
            "path": "AlgebraicCombinatorics/Toy.lean",
            "declaration": "Toy.futureHelper",
            "line_range": [5, 6],
            "method": "local_predecessor_window",
            "reason": "Bad future predecessor.",
        }
    ]

    result = review(tmp_path, record)

    assert result.verdict == "reject"
    assert any("not strictly before" in issue for issue in result.label_or_line_issues)


def test_static_review_marks_unreferenced_predecessor_for_revision(tmp_path: Path) -> None:
    write_project(
        tmp_path,
        "\n".join(
            [
                "namespace Toy",
                "theorem helper : True := by",
                "  trivial",
                "/-- Theorem \\ref{thm.toy}. -/",
                "theorem target : True := by",
                "  trivial",
                "end Toy",
            ]
        )
        + "\n",
        "\\label{thm.toy}\nStatement.\nProof.\n",
    )
    record = base_record()
    record["output"]["line_range"] = [4, 6]
    record["minimal_context"]["lean_predecessors"] = [
        {
            "path": "AlgebraicCombinatorics/Toy.lean",
            "declaration": "Toy.helper",
            "line_range": [2, 3],
            "method": "local_predecessor_window",
            "reason": "Nearest preceding declaration in the same Lean file.",
        }
    ]

    result = review(tmp_path, record)

    assert result.verdict == "revise"
    assert any("not named" in issue for issue in result.oversized_context)
