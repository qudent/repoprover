"""Tests for LaTeX-statement-level dataset generation."""

from pathlib import Path

from scripts.generate_latex_statement_dataset import (
    build_label_indexes,
    extract_declared_source_labels,
    parse_latex_statement_units,
    parse_lean_label_declarations,
    row_for_unit,
)


def test_parse_latex_statement_units_extracts_one_environment_and_parts(tmp_path: Path) -> None:
    project = tmp_path
    tex_dir = project / "AlgebraicCombinatorics" / "tex" / "Toy"
    tex_dir.mkdir(parents=True)
    (tex_dir / "Demo.tex").write_text(
        "\n".join(
            [
                "Before.",
                "\\begin{lemma}",
                "\\label{lem.demo}Let $n\\in\\mathbb{N}$. Then:",
                "\\textbf{(a)} First part.",
                "\\textbf{(b)} Second part, using Theorem \\ref{thm.prev}.",
                "\\end{lemma}",
                "\\begin{proof}Not part of the source unit.\\end{proof}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (project / "manifest.json").write_text(
        '{"chapters":[{"id":"demo","source_path":"AlgebraicCombinatorics/tex/Toy/Demo.tex","target_theorems":["lem.demo"]}]}',
        encoding="utf-8",
    )

    units = parse_latex_statement_units(project)

    assert len(units) == 1
    unit = units[0]
    assert unit.id == "AlgebraicCombinatorics/tex/Toy/Demo.tex:lem.demo"
    assert unit.environment == "lemma"
    assert unit.line_range == (2, 6)
    assert unit.labels == ("lem.demo",)
    assert unit.referenced_labels == ("thm.prev",)
    assert [part["part"] for part in unit.part_markers] == ["a", "b"]
    assert unit.manifest_target_labels == ("lem.demo",)
    assert "proof" not in unit.source_text.lower()


def test_parse_latex_statement_units_keeps_nested_statement_units(tmp_path: Path) -> None:
    project = tmp_path
    tex_dir = project / "AlgebraicCombinatorics" / "tex"
    tex_dir.mkdir(parents=True)
    (tex_dir / "Demo.tex").write_text(
        "\n".join(
            [
                "\\begin{proposition}",
                "\\label{prop.outer}Outer claim.",
                "\\begin{proof}",
                "\\begin{statement}",
                "Inner observation.",
                "\\end{statement}",
                "\\end{proof}",
                "\\end{proposition}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (project / "manifest.json").write_text(
        '{"chapters":[{"id":"demo","source_path":"AlgebraicCombinatorics/tex/Demo.tex","target_theorems":["prop.outer"]}]}',
        encoding="utf-8",
    )

    units = parse_latex_statement_units(project)

    assert [(unit.environment, unit.line_range) for unit in units] == [
        ("proposition", (1, 8)),
        ("statement", (4, 6)),
    ]


def test_parse_latex_statement_units_keeps_mismatched_close_with_warning(tmp_path: Path) -> None:
    project = tmp_path
    tex_dir = project / "AlgebraicCombinatorics" / "tex"
    tex_dir.mkdir(parents=True)
    (tex_dir / "Demo.tex").write_text(
        "\\begin{definition}\\label{def.mismatch}Text.\\end{example}\n",
        encoding="utf-8",
    )
    (project / "manifest.json").write_text(
        '{"chapters":[{"id":"demo","source_path":"AlgebraicCombinatorics/tex/Demo.tex","target_theorems":["def.mismatch"]}]}',
        encoding="utf-8",
    )

    units = parse_latex_statement_units(project)

    assert len(units) == 1
    assert units[0].environment == "definition"
    assert units[0].parse_warnings == ("mismatched_end_environment:example",)


def test_extract_declared_source_labels_ignores_plain_refs() -> None:
    comment = "\n".join(
        [
            "/-- Uses Definition \\ref{def.support}.",
            "    Label: lem.demo.a -/",
        ]
    )

    assert extract_declared_source_labels(comment) == ("lem.demo.a",)


def test_lean_alignment_uses_declared_label_not_reference(tmp_path: Path) -> None:
    project = tmp_path
    tex_dir = project / "AlgebraicCombinatorics" / "tex"
    lean_dir = project / "AlgebraicCombinatorics"
    tex_dir.mkdir(parents=True)
    lean_dir.mkdir(exist_ok=True)
    (tex_dir / "Demo.tex").write_text(
        "\\begin{lemma}\\label{lem.demo}Demo.\\end{lemma}\n",
        encoding="utf-8",
    )
    (project / "manifest.json").write_text(
        '{"chapters":[{"id":"demo","source_path":"AlgebraicCombinatorics/tex/Demo.tex","target_theorems":["lem.demo"]}]}',
        encoding="utf-8",
    )
    (lean_dir / "Demo.lean").write_text(
        "\n".join(
            [
                "namespace Demo",
                "/-- Helper that only references \\ref{lem.demo}. -/",
                "theorem helper : True := by",
                "  trivial",
                "",
                "/-- Formalized source part.",
                "    Label: lem.demo.a -/",
                "theorem target : True := by",
                "  trivial",
                "end Demo",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    units = parse_latex_statement_units(project)
    lean_rows = parse_lean_label_declarations(project)
    declared_index, referenced_index = build_label_indexes(lean_rows)
    row = row_for_unit(
        units[0],
        units=units,
        declared_index=declared_index,
        referenced_index=referenced_index,
        generated_at="2026-05-05T00:00:00+00:00",
    )

    aligned = row["posthoc_lean_alignment"]["aligned_lean_declarations"]
    references = row["posthoc_lean_alignment"]["referencing_lean_declarations"]
    assert [decl["full_name"] for decl in aligned] == ["Demo.target"]
    assert [decl["full_name"] for decl in references] == ["Demo.helper"]
    assert row["selection"]["status"] == "gold_candidate"
