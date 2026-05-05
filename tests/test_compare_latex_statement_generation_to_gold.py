"""Tests for post-hoc theorem-level gold comparison."""

import json
from pathlib import Path

from scripts.compare_latex_statement_generation_to_gold import compare


def test_compare_reports_compile_without_name_overlap(tmp_path: Path) -> None:
    selector = tmp_path / "selector"
    generation = tmp_path / "generation"
    (selector / "eval").mkdir(parents=True)
    (generation / "batch-001").mkdir(parents=True)
    (generation / "eval").mkdir()
    selected = {
        "id": "source:demo",
        "posthoc_lean_alignment": {
            "aligned_lean_declarations": [
                {"full_name": "Demo.gold_name"},
            ]
        },
    }
    (selector / "eval/selected-units.jsonl").write_text(json.dumps(selected) + "\n", encoding="utf-8")
    (generation / "batch-001/generation-output.json").write_text(
        json.dumps({"units": [{"unit_key": "unit-001", "declaration_names": ["other_name"]}]}),
        encoding="utf-8",
    )
    (generation / "eval/verification-results.json").write_text(
        json.dumps({"batches": [{"units": [{"unit_key": "unit-001", "compile_passed": True}]}]}),
        encoding="utf-8",
    )

    summary = compare(selector, generation)

    assert summary["compile_passed_units"] == 1
    assert summary["compiled_name_overlap_units"] == 0
    assert summary["compiled_needs_semantic_review_units"] == 1
    assert summary["units"][0]["coverage_status"] == "compiled_needs_semantic_review"
