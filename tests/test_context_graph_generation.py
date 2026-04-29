"""Tests for whole-corpus context graph generation helpers."""

from pathlib import Path

from scripts.generate_context_graph import (
    find_predecessors,
    module_path_index,
    TexLabel,
    clean_label_token,
    parse_lean_declarations,
    parse_tex_labels,
    should_replace_tex_label,
)


def test_clean_label_token_preserves_balanced_parentheses() -> None:
    assert clean_label_token("def.det.sub)") == "def.det.sub"
    assert clean_label_token("thm.det.det(A+B)") == "thm.det.det(A+B)"
    assert clean_label_token("prop.binom.rec,") == "prop.binom.rec"
    assert clean_label_token("thm.det.adj.inverse**") == "thm.det.adj.inverse"
    assert clean_label_token("eq.thm.fps.xneq.props.b.*") == "eq.thm.fps.xneq.props.b.*"


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


def test_parse_tex_labels_ignores_refs(tmp_path: Path) -> None:
    project = tmp_path
    tex_dir = project / "AlgebraicCombinatorics" / "tex"
    tex_dir.mkdir(parents=True)
    tex_file = tex_dir / "Toy.tex"
    tex_file.write_text(
        "\n".join(
            [
                "See \\ref{thm.only.ref}.",
                "\\begin{theorem}\\label{thm.real.label}",
                "Real theorem.",
                "\\end{theorem}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    labels = parse_tex_labels(project)

    assert "thm.only.ref" not in labels
    assert labels["thm.real.label"].line == 2


def test_parse_lean_declarations_tracks_namespace_and_doc_labels(tmp_path: Path) -> None:
    project = tmp_path
    lean_dir = project / "AlgebraicCombinatorics"
    lean_dir.mkdir()
    lean_file = lean_dir / "Toy.lean"
    lean_file.write_text(
        "\n".join(
            [
                "import Mathlib",
                "open Nat",
                "namespace AlgebraicCombinatorics",
                "variable {R : Type*} [CommRing R]",
                "/-- Definition \\ref{def.toy.item}. -/",
                "def toyItem : R → Nat := fun _ => 1",
                "",
                "/-- Theorem thm.toy.item) follows. -/",
                "theorem toyItem_eq (r : R) : toyItem r = 1 := rfl",
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
    assert [span["kind"] for span in declarations[0].file_context] == ["open", "namespace", "variable"]
    assert declarations[0].file_context[1]["name"] == "AlgebraicCombinatorics"
    assert declarations[0].file_context[2]["name"] == "variable {R : Type*} [CommRing R]"


def test_parse_lean_declarations_pops_named_sections_without_losing_namespace(tmp_path: Path) -> None:
    project = tmp_path
    lean_dir = project / "AlgebraicCombinatorics"
    lean_dir.mkdir()
    lean_file = lean_dir / "Toy.lean"
    lean_file.write_text(
        "\n".join(
            [
                "namespace Outer",
                "section Local",
                "variable {R : Type*}",
                "def first : Nat := 1",
                "end Local",
                "def second : Nat := 2",
                "end Outer",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    declarations = parse_lean_declarations(project, lean_file)

    assert [row.full_name for row in declarations] == ["Outer.first", "Outer.second"]
    assert [span["kind"] for span in declarations[0].file_context] == ["namespace", "section", "variable"]
    assert [span["kind"] for span in declarations[1].file_context] == ["namespace"]


def test_find_predecessors_keeps_local_window_optional(tmp_path: Path) -> None:
    project = tmp_path
    lean_dir = project / "AlgebraicCombinatorics"
    lean_dir.mkdir()
    lean_file = lean_dir / "Toy.lean"
    lean_file.write_text(
        "\n".join(
            [
                "namespace Toy",
                "theorem helper : True := by",
                "  trivial",
                "",
                "theorem target : True := by",
                "  trivial",
                "end Toy",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    declarations = parse_lean_declarations(project, lean_file)
    declarations_by_module = module_path_index(declarations)
    direct_imports = {}
    by_short_name = {row.name: [row] for row in declarations}

    strict_predecessors, _ = find_predecessors(
        declarations[1],
        declarations_by_module,
        direct_imports,
        by_short_name,
        project,
        local_window=0,
        max_references=0,
    )
    window_predecessors, _ = find_predecessors(
        declarations[1],
        declarations_by_module,
        direct_imports,
        by_short_name,
        project,
        local_window=1,
        max_references=0,
    )

    assert strict_predecessors == []
    assert [row["declaration"] for row in window_predecessors] == ["Toy.helper"]
    assert window_predecessors[0]["method"] == "local_predecessor_window"
