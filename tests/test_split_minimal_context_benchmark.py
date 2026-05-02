"""Tests for honest minimal-context benchmark splitting."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.split_minimal_context_benchmark import split_records, write_splits


def _fixture_records() -> list[dict]:
    return [
        {
            "id": "Demo.lean:Demo.first",
            "chapter_id": "demo",
            "output": {
                "lean_path": "Demo.lean",
                "declaration_names": ["Demo.first"],
                "line_range": [10, 12],
                "chunk_kind": "theorem",
            },
            "minimal_context": {
                "imports": ["Mathlib"],
                "import_closure": ["Mathlib"],
                "file_context": [
                    {"path": "Demo.lean", "line_range": [1, 1], "kind": "namespace", "name": "Demo"},
                    {"path": "Demo.lean", "line_range": [11, 11], "kind": "variable", "name": "variable (tooLate : True)"},
                ],
                "lean_predecessors": [
                    {"path": "Demo.lean", "line_range": [3, 5], "declaration_names": ["Demo.prev"]},
                    {"path": "Demo.lean", "line_range": [12, 14], "declaration_names": ["Demo.future"]},
                    {"path": "Other.lean", "line_range": [1, 2], "declaration_names": ["Other.imported"]},
                ],
                "source_spans": [
                    {"path": "Demo.tex", "line_range": [20, 25], "labels": ["target.label"], "method": "lean_comment_label"}
                ],
                "mathlib_context": ["Mathlib context"],
            },
        }
    ]


def test_split_records_marks_tracks_and_filters_prefix_context() -> None:
    splits = split_records(_fixture_records(), source_prefix_window=7)

    assert set(splits) == {"oracle_proof_fill", "oracle_source_statement", "prefix_next_declaration"}
    assert all(len(rows) == 1 for rows in splits.values())

    oracle = splits["oracle_proof_fill"][0]
    assert oracle["benchmark_metadata"]["track"] == "oracle_proof_fill"
    assert oracle["benchmark_metadata"]["leakage_level"] == "oracle_upper_bound"
    assert oracle["minimal_context"]["source_spans"][0]["labels"] == ["target.label"]
    assert oracle["target_policy"]["lean_statement_available"] is True

    statement = splits["oracle_source_statement"][0]
    assert statement["benchmark_metadata"]["track"] == "oracle_source_statement"
    assert statement["target_policy"]["lean_statement_available"] is False
    assert [p["declaration_names"][0] for p in statement["minimal_context"]["lean_predecessors"]] == [
        "Demo.prev"
    ]
    assert [span["line_range"] for span in statement["minimal_context"]["file_context"]] == [[1, 1]]
    assert statement["minimal_context"]["source_spans"][0]["labels"] == ["target.label"]

    prefix = splits["prefix_next_declaration"][0]
    assert prefix["benchmark_metadata"]["track"] == "prefix_next_declaration"
    assert prefix["benchmark_metadata"]["leakage_level"] == "honest_prefix_with_documented_source_alignment_limitations"
    assert prefix["target_policy"]["lean_statement_available"] is False
    assert prefix["minimal_context"]["source_spans"] == [
        {
            "path": "Demo.tex",
            "line_range": [13, 19],
            "method": "prefix_window_before_aligned_target_span",
            "reason": "Prefix TeX window ending strictly before aligned target source span; target span itself is withheld.",
            "source_context_derived_from_target_alignment": True,
            "labels": [],
        }
    ]
    assert [p["declaration_names"][0] for p in prefix["minimal_context"]["lean_predecessors"]] == ["Demo.prev"]


def test_write_splits_emits_jsonl_manifest_and_report(tmp_path: Path) -> None:
    output_dir = tmp_path / "splits"
    manifest = write_splits(_fixture_records(), output_dir, source_prefix_window=3)

    assert manifest["schema_version"] == "repoprover.minimal_context_splits.v1"
    assert manifest["total_input_records"] == 1
    assert sorted(p.name for p in output_dir.glob("*.jsonl")) == [
        "oracle_proof_fill.jsonl",
        "oracle_source_statement.jsonl",
        "prefix_next_declaration.jsonl",
    ]
    report = (output_dir / "README.md").read_text(encoding="utf-8")
    assert "oracle_proof_fill" in report
    assert "prefix_next_declaration" in report
    assert "target-derived" in report

    prefix_line = (output_dir / "prefix_next_declaration.jsonl").read_text(encoding="utf-8").strip()
    prefix_record = json.loads(prefix_line)
    assert prefix_record["minimal_context"]["source_spans"][0]["line_range"] == [17, 19]
