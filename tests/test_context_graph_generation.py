"""Tests for whole-corpus context graph generation helpers."""

from pathlib import Path

from scripts.generate_context_graph import (
    TexLabel,
    clean_label_token,
    parse_lean_declarations,
    should_replace_tex_label,
)


def test_clean_label_token_preserves_balanced_parentheses() -> None:
    assert clean_label_token("def.det.sub)") == "def.det.sub"
    assert clean_label_token("thm.det.det(A+B)") == "thm.det.det(A+B)"
    assert clean_label_token("prop.binom.rec,") == "prop.binom.rec"


def test_prefers_chapter_tex_label_over_aggregate_all_tex() -> None:
    aggregate = TexLabel(
        label="def.det.sub",
        path="AlgebraicCombinatorics/tex/all.tex",
        line=10,
        line_range=(10, 12),
        kind="def",
    )
    chapter = TexLabel(
        label="def.det.sub",
        path="AlgebraicCombinatorics/tex/Determinants/CauchyBinet.tex",
        line=223,
        line_range=(223, 300),
        kind="def",
    )

    assert should_replace_tex_label(aggregate, chapter)
    assert not should_replace_tex_label(chapter, aggregate)


def test_parse_lean_declarations_tracks_namespace_and_doc_labels(tmp_path: Path) -> None:
    project = tmp_path
    lean_dir = project / "AlgebraicCombinatorics"
    lean_dir.mkdir()
    lean_file = lean_dir / "Toy.lean"
    lean_file.write_text(
        "\n".join(
            [
                "import Mathlib",
                "namespace AlgebraicCombinatorics",
                "/-- Definition \\ref{def.toy.item}. -/",
                "def toyItem : Nat := 1",
                "",
                "/-- Theorem thm.toy.item) follows. -/",
                "theorem toyItem_eq : toyItem = 1 := rfl",
                "end AlgebraicCombinatorics",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    declarations = parse_lean_declarations(project, lean_file)

    assert [row.full_name for row in declarations] == [
        "AlgebraicCombinatorics.toyItem",
        "AlgebraicCombinatorics.toyItem_eq",
    ]
    assert declarations[0].comment_labels == ("def.toy.item",)
    assert declarations[1].comment_labels == ("thm.toy.item",)
    assert declarations[1].imports == ("Mathlib",)
