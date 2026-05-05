"""Tests for minimal-context RepoProver smoke materialization."""

from pathlib import Path

import pytest

from scripts.materialize_minimal_context_smoke import (
    SelectedRecord,
    build_target_lean,
    context_close_commands,
    copy_lake_cache,
    declarations_in_file,
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


def test_context_close_commands_preserves_named_sections() -> None:
    closes = context_close_commands(
        [
            {"kind": "namespace", "name": "Outer"},
            {"kind": "section", "name": "Local"},
        ]
    )

    assert closes == ["end Local", "end Outer"]


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


def test_materialize_smoke_project_uses_file_context_and_mathlib_only_default(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    source_root.mkdir()
    (source_root / "lakefile.lean").write_text("import Lake\n", encoding="utf-8")
    (source_root / "lean-toolchain").write_text("leanprover/lean4:v4.28.0\n", encoding="utf-8")

    lean_dir = source_root / "Demo"
    lean_dir.mkdir()
    (lean_dir / "Context.lean").write_text(
        "\n".join(
            [
                "import Mathlib",
                "open Nat",
                "namespace Demo",
                "variable {n : Nat}",
                "",
                "lemma helper : True := by",
                "  trivial",
                "",
                "/-- Target theorem. -/",
                "theorem target : True := by",
                "  exact helper",
                "",
                "end Demo",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (source_root / "Demo.tex").write_text("target text\n", encoding="utf-8")

    record = SelectedRecord(
        {
            "id": "demo:target",
            "chapter_id": "demo",
            "output": {
                "lean_path": "Demo/Context.lean",
                "declaration_names": ["Demo.target"],
                "line_range": [9, 11],
                "chunk_kind": "theorem",
            },
            "minimal_context": {
                "imports": ["Mathlib", "Demo.LocalDependency"],
                "source_spans": [{"path": "Demo.tex", "line_range": [1, 1], "labels": ["target"]}],
                "file_context": [
                    {"path": "Demo/Context.lean", "kind": "open", "name": "open Nat", "line_range": [2, 2]},
                    {"path": "Demo/Context.lean", "kind": "namespace", "name": "Demo", "line_range": [3, 3]},
                    {"path": "Demo/Context.lean", "kind": "variable", "name": "variable {n : Nat}", "line_range": [4, 4]},
                ],
                "lean_predecessors": [
                    {"path": "Demo/Context.lean", "declaration": "Demo.helper", "line_range": [6, 7]}
                ],
            },
        }
    )

    output_root = tmp_path / "smoke"
    materialize_smoke_project(source_root, output_root, [record], init_git=False)

    lean_text = (output_root / "Demo" / "Context.lean").read_text(encoding="utf-8")
    assert "import Mathlib\n" in lean_text
    assert "import Demo.LocalDependency" not in lean_text
    assert "open Nat" in lean_text
    assert "namespace Demo" in lean_text
    assert "variable {n : Nat}" in lean_text
    assert "lemma helper : True := by\n  trivial" in lean_text
    assert "theorem target : True := by\n  sorry" in lean_text
    assert "exact helper" not in lean_text
    assert lean_text.rstrip().endswith("end Demo")


def test_build_target_lean_preserves_file_context_chronology_around_predecessors(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    source_root.mkdir()
    lean_dir = source_root / "Demo"
    lean_dir.mkdir()
    (lean_dir / "Order.lean").write_text(
        "\n".join(
            [
                "import Mathlib",
                "namespace Demo",
                "variable (K : Type*)",
                "",
                "def helper : Type* := K",
                "",
                "variable {K}",
                "",
                "theorem target : helper K = helper K := by",
                "  rfl",
                "",
                "end Demo",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    record = SelectedRecord(
        {
            "id": "demo:target",
            "output": {
                "lean_path": "Demo/Order.lean",
                "declaration_names": ["Demo.target"],
                "line_range": [9, 10],
                "chunk_kind": "theorem",
            },
            "minimal_context": {
                "file_context": [
                    {"path": "Demo/Order.lean", "kind": "namespace", "name": "Demo", "line_range": [2, 2]},
                    {"path": "Demo/Order.lean", "kind": "variable", "name": "variable (K : Type*)", "line_range": [3, 3]},
                    {"path": "Demo/Order.lean", "kind": "variable", "name": "variable {K}", "line_range": [7, 7]},
                ],
                "lean_predecessors": [
                    {"path": "Demo/Order.lean", "declaration": "Demo.helper", "line_range": [5, 5]},
                ],
            },
        }
    )

    lean_text = build_target_lean(source_root, record)

    assert lean_text.index("variable (K : Type*)") < lean_text.index("def helper")
    assert lean_text.index("def helper") < lean_text.index("variable {K}")
    assert lean_text.index("variable {K}") < lean_text.index("theorem target")


def test_build_target_lean_adds_transitive_same_file_predecessors(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    source_root.mkdir()
    lean_dir = source_root / "Demo"
    lean_dir.mkdir()
    (lean_dir / "Deps.lean").write_text(
        "\n".join(
            [
                "import Mathlib",
                "namespace Demo",
                "",
                "theorem base : True := by",
                "  trivial",
                "",
                "theorem mid : True := by",
                "  exact base",
                "",
                "theorem target : True := by",
                "  exact mid",
                "",
                "end Demo",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    record = SelectedRecord(
        {
            "id": "demo:target",
            "output": {
                "lean_path": "Demo/Deps.lean",
                "declaration_names": ["Demo.target"],
                "line_range": [10, 11],
                "chunk_kind": "theorem",
            },
            "minimal_context": {
                "file_context": [
                    {"path": "Demo/Deps.lean", "kind": "namespace", "name": "Demo", "line_range": [2, 2]},
                ],
                "lean_predecessors": [
                    {"path": "Demo/Deps.lean", "declaration": "Demo.mid", "line_range": [7, 8]},
                ],
            },
        }
    )

    lean_text = build_target_lean(source_root, record)

    assert "theorem base : True := by\n  trivial" in lean_text
    assert lean_text.index("theorem base") < lean_text.index("theorem mid")
    assert lean_text.count("theorem mid") == 1


def test_declarations_in_file_trims_trailing_doc_blocks_from_predecessors(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    source_root.mkdir()
    (source_root / "Demo.lean").write_text(
        "\n".join(
            [
                "namespace Demo",
                "",
                "/-- First declaration. -/",
                "theorem first : True := by",
                "  trivial",
                "",
                "/-!",
                "Standalone section text for the next declaration.",
                "-/",
                "",
                "/-- Second declaration. -/",
                "theorem second : True := by",
                "  trivial",
                "",
                "end Demo",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    declarations = declarations_in_file(source_root, "Demo.lean")
    first = next(row for row in declarations if row["declaration"] == "Demo.first")

    assert first["line_range"] == [3, 5]


def test_copy_lake_cache_decompresses_missing_mathlib_oleans(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cache_from = tmp_path / "source"
    source_lake = cache_from / ".lake"
    (source_lake / "packages" / "mathlib").mkdir(parents=True)
    (cache_from / "lakefile.lean").write_text("import Lake\n", encoding="utf-8")
    output_root = tmp_path / "out"
    output_root.mkdir()
    calls = []

    def fake_run(*args: object, **kwargs: object) -> object:
        calls.append((args, kwargs))
        mathlib_olean = (
            source_lake / "packages" / "mathlib" / ".lake" / "build" / "lib" / "lean" / "Mathlib.olean"
        )
        mathlib_olean.parent.mkdir(parents=True)
        mathlib_olean.write_text("", encoding="utf-8")
        return object()

    monkeypatch.setattr("scripts.materialize_minimal_context_smoke.subprocess.run", fake_run)

    copy_lake_cache(cache_from, output_root)

    assert calls
    command = calls[0][0][0]
    assert command == ["uv", "run", "lake", "exe", "cache", "get", "Mathlib"]
    assert (output_root / ".lake" / "packages").is_symlink()
    assert (output_root / ".lake" / "packages").resolve() == (source_lake / "packages").resolve()


def test_copy_lake_cache_skips_decompression_when_mathlib_olean_exists(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cache_from = tmp_path / "source"
    source_lake = cache_from / ".lake"
    mathlib_olean = source_lake / "packages" / "mathlib" / ".lake" / "build" / "lib" / "lean" / "Mathlib.olean"
    mathlib_olean.parent.mkdir(parents=True)
    mathlib_olean.write_text("", encoding="utf-8")
    (cache_from / "lakefile.lean").write_text("import Lake\n", encoding="utf-8")
    output_root = tmp_path / "out"
    output_root.mkdir()

    def fail_run(*args: object, **kwargs: object) -> object:
        raise AssertionError("cache get should not run when Mathlib.olean exists")

    monkeypatch.setattr("scripts.materialize_minimal_context_smoke.subprocess.run", fail_run)

    copy_lake_cache(cache_from, output_root)

    assert (output_root / ".lake" / "packages").is_symlink()
    assert (output_root / ".lake" / "packages").resolve() == (source_lake / "packages").resolve()
