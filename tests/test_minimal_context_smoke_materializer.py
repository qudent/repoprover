"""Tests for minimal-context RepoProver smoke materialization."""

from pathlib import Path

from scripts.materialize_minimal_context_smoke import (
    SelectedRecord,
    materialize_smoke_project,
    select_records,
)


def test_select_records_prefers_reviewed_short_theorem() -> None:
    rows = [
        {
            "id": "low",
            "output": {
                "chunk_kind": "theorem",
                "declaration_names": ["Demo.low"],
                "line_range": [1, 20],
            },
            "trust": {"human_review": 0.0, "source_span": 0.9, "lean_dependency_graph": 0.9},
        },
        {
            "id": "high",
            "output": {
                "chunk_kind": "theorem",
                "declaration_names": ["Demo.high"],
                "line_range": [1, 3],
            },
            "trust": {"human_review": 0.3, "source_span": 0.65, "lean_dependency_graph": 0.55},
        },
    ]

    assert select_records(rows, [], 1)[0].record_id == "high"


def test_materialize_smoke_project_writes_single_sorry_project(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    source_root.mkdir()
    (source_root / "lakefile.lean").write_text(
        "\n".join(
            [
                "import Lake",
                "",
                "require checkdecls from git",
                '  "https://github.com/PatrickMassot/checkdecls.git"',
                "",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (source_root / "lean-toolchain").write_text("leanprover/lean4:v4.28.0\n", encoding="utf-8")

    lean_dir = source_root / "Demo"
    lean_dir.mkdir()
    (lean_dir / "Example.lean").write_text(
        "\n".join(
            [
                "import Mathlib",
                "namespace Demo",
                "",
                "/-- A small wrapper theorem. -/",
                "theorem obvious : True := by",
                "  exact True.intro",
                "",
                "end Demo",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    tex_dir = source_root / "Demo" / "tex"
    tex_dir.mkdir()
    (tex_dir / "Example.tex").write_text("line one\nline two\nline three\n", encoding="utf-8")

    record = SelectedRecord(
        {
            "id": "demo:obvious",
            "chapter_id": "demo",
            "output": {
                "lean_path": "Demo/Example.lean",
                "declaration_names": ["Demo.obvious"],
                "line_range": [4, 6],
                "chunk_kind": "theorem",
            },
            "minimal_context": {
                "imports": ["Mathlib"],
                "source_spans": [
                    {
                        "path": "Demo/tex/Example.tex",
                        "line_range": [2, 3],
                        "labels": ["thm.demo.obvious"],
                    }
                ],
                "lean_predecessors": [],
                "mathlib_context": ["True.intro"],
            },
            "trust": {"human_review": 0.3, "source_span": 0.8},
        }
    )

    output_root = tmp_path / "smoke"
    materialize_smoke_project(source_root, output_root, [record], init_git=False)

    lean_text = (output_root / "Demo" / "Example.lean").read_text(encoding="utf-8")
    assert "namespace Demo" in lean_text
    assert "theorem obvious : True := by\n  sorry" in lean_text
    assert "exact True.intro" not in lean_text

    assert (output_root / "Demo.lean").read_text(encoding="utf-8") == "import Demo.Example\n"
    assert "checkdecls" not in (output_root / "lakefile.lean").read_text(encoding="utf-8")
    assert ".lake/" in (output_root / ".gitignore").read_text(encoding="utf-8")
    assert "line two\nline three" in (output_root / "Demo" / "tex" / "Example.tex").read_text(encoding="utf-8")

    state_text = (output_root / ".repoprover" / "state.json").read_text(encoding="utf-8")
    assert '"sketch_merged": true' in state_text
    assert '"target_theorems": [\n        "obvious"\n      ]' in state_text
