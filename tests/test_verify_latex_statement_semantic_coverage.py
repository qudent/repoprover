"""Tests for post-hoc theorem-level semantic coverage checks."""

from argparse import Namespace
from pathlib import Path

from scripts.verify_latex_statement_semantic_coverage import build_semantic_check_source, compare


def test_build_semantic_check_source_uses_gold_only_in_grader(tmp_path: Path) -> None:
    project = tmp_path / "project"
    lean_file = project / "Demo.lean"
    lean_file.parent.mkdir(parents=True)
    lean_file.write_text(
        "\n".join(
            [
                "import Mathlib",
                "namespace Demo",
                "variable {α : Type}",
                "theorem gold {p : Prop} (h : p) : p := by",
                "  exact h",
                "end Demo",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    aligned = {"path": "Demo.lean", "line_range": [4, 5], "kind": "theorem"}

    source = build_semantic_check_source(
        project_root=project,
        aligned=aligned,
        generated_names=["generated"],
        generated_body="theorem generated {p : Prop} (h : p) : p := by\n  exact h",
    )

    assert "theorem gold" not in source
    assert "theorem __repoprover_latex_statement_check" in source
    assert "simpa using generated h" in source


def test_compare_records_semantic_failure(monkeypatch, tmp_path: Path) -> None:
    project = tmp_path / "project"
    selector = tmp_path / "selector"
    generation = tmp_path / "generation"
    project.mkdir()
    (selector / "eval").mkdir(parents=True)
    (generation / "batch-001").mkdir(parents=True)
    (generation / "eval").mkdir()
    (project / "Demo.lean").write_text(
        "\n".join(
            [
                "import Mathlib",
                "namespace Demo",
                "theorem gold (p : Prop) (h : p) : p := by",
                "  exact h",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (selector / "eval/selected-units.jsonl").write_text(
        '{"id":"source:demo","posthoc_lean_alignment":{"aligned_lean_declarations":[{"full_name":"Demo.gold","kind":"theorem","path":"Demo.lean","line_range":[3,4]}]}}\n',
        encoding="utf-8",
    )
    (generation / "batch-001/generation-output.json").write_text(
        '{"units":[{"unit_key":"unit-001","lean_file_body":"theorem generated : True := by\\n  trivial","declaration_names":["generated"]}]}\n',
        encoding="utf-8",
    )
    (generation / "eval/verification-results.json").write_text(
        '{"batches":[{"units":[{"unit_key":"unit-001","compile_passed":true}]}]}\n',
        encoding="utf-8",
    )

    def fake_run_lean_file(path: Path, *, project_root: Path, timeout_seconds: float):
        assert path.exists()
        return {
            "returncode": 1,
            "messages": [{"severity": "error", "data": "Application type mismatch"}],
            "stderr": "",
        }

    monkeypatch.setattr("scripts.verify_latex_statement_semantic_coverage.run_lean_file", fake_run_lean_file)

    summary = compare(
        Namespace(
            selector_run=selector,
            generation_run=generation,
            project_root=project,
            timeout_seconds=1.0,
            verification_results=None,
            output=generation / "eval/semantic-coverage.json",
        )
    )

    assert summary["unit_count"] == 1
    assert summary["no_aligned_gold_proved_units"] == 1
    assert summary["units"][0]["coverage_status"] == "no_aligned_gold_proved"
    assert summary["units"][0]["checks"][0]["coverage_status"] == "semantic_grader_failed"
    assert summary["units"][0]["checks"][0]["failure_class"] == "shape_mismatch_against_oracle"
