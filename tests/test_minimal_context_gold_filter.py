"""Tests for deterministic minimal-context gold-candidate selection."""

from __future__ import annotations

from pathlib import Path

from scripts.filter_minimal_context_gold_candidates import (
    SelectionConfig,
    SpanValidator,
    rejection_reasons,
    select_records,
)


def sample_record() -> dict:
    return {
        "id": "Toy.lean:Demo.target",
        "chapter_id": "toy",
        "output": {
            "lean_path": "Toy.lean",
            "declaration_names": ["Demo.target"],
            "line_range": [3, 5],
            "chunk_kind": "theorem",
        },
        "minimal_context": {
            "source_spans": [
                {
                    "path": "Toy.tex",
                    "line_range": [2, 4],
                    "labels": ["thm.toy"],
                    "method": "lean_comment_label",
                    "reason": "Lean doc comment references this TeX label.",
                }
            ],
            "lean_predecessors": [
                {
                    "path": "Toy.lean",
                    "declaration": "Demo.helper",
                    "line_range": [1, 2],
                    "method": "local_predecessor_window",
                    "reason": "Nearest preceding declaration in the same Lean file.",
                }
            ],
            "imports": ["Mathlib"],
            "import_closure": ["Mathlib"],
            "mathlib_context": [],
        },
        "alignment": {
            "source_method": "lean_comment_label",
            "comment_labels": ["thm.toy"],
            "paired_source_path": "Toy.tex",
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


def test_select_records_accepts_exact_label_with_valid_bounded_spans(tmp_path: Path) -> None:
    (tmp_path / "Toy.lean").write_text("lemma helper : True := by\n  trivial\n\ntheorem target : True := by\n  trivial\n")
    (tmp_path / "Toy.tex").write_text("intro\n\\label{thm.toy}\nstatement\nproof\n")

    selected, reason_counts, _ = select_records(
        [sample_record()],
        SelectionConfig(),
        SpanValidator(tmp_path),
        selected_at="2026-04-28T00:00:00+00:00",
    )

    assert len(selected) == 1
    assert selected[0]["selection"]["status"] == "gold_candidate"
    assert selected[0]["selection"]["criteria"]["source_method"] == "lean_comment_label"
    assert reason_counts == {}


def test_rejection_reasons_reject_position_fallback_and_oversized_output() -> None:
    record = sample_record()
    record["alignment"]["source_method"] = "manifest_position_fallback"
    record["minimal_context"]["source_spans"][0]["method"] = "manifest_position_fallback"
    record["output"]["line_range"] = [3, 200]

    reasons = rejection_reasons(record, SelectionConfig(max_output_lines=50))

    assert "source_method_not_lean_comment_label" in reasons
    assert "source_span_method_mismatch" in reasons
    assert "output_span_too_large" in reasons


def test_rejection_reasons_validate_missing_or_out_of_bounds_paths(tmp_path: Path) -> None:
    (tmp_path / "Toy.lean").write_text("theorem target : True := by\n  trivial\n")
    record = sample_record()
    record["output"]["line_range"] = [1, 3]

    reasons = rejection_reasons(record, SelectionConfig(), SpanValidator(tmp_path))

    assert "source_missing_path" in reasons
    assert "output_invalid_line_range" in reasons
