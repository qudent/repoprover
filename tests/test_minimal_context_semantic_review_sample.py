"""Tests for semantic-review sample selection."""

from __future__ import annotations

from scripts.sample_minimal_context_semantic_review import (
    difficulty_bin,
    difficulty_score,
    select_sample,
    stratum_for_record,
)


def record(record_id: str, *, kind: str = "theorem", source_lines: int = 5, output_lines: int = 5) -> dict:
    return {
        "id": record_id,
        "chapter_id": "toy",
        "output": {
            "lean_path": "Toy.lean",
            "declaration_names": [record_id],
            "line_range": [1, output_lines],
            "chunk_kind": kind,
        },
        "minimal_context": {
            "source_spans": [
                {
                    "path": "Toy.tex",
                    "line_range": [1, source_lines],
                    "labels": ["thm.toy"],
                    "method": "lean_comment_label",
                }
            ],
            "lean_predecessors": [],
        },
    }


def test_difficulty_bin_uses_context_size() -> None:
    small = record("small", source_lines=10, output_lines=10)
    medium = record("medium", source_lines=70, output_lines=10)
    large = record("large", source_lines=100, output_lines=20)

    assert difficulty_score(small) == 20
    assert difficulty_bin(difficulty_score(small)) == "small"
    assert difficulty_bin(difficulty_score(medium)) == "medium"
    assert difficulty_bin(difficulty_score(large)) == "large"


def test_select_sample_keeps_only_static_accepts_and_caps_strata() -> None:
    records = [
        record("def-small-1", kind="def", source_lines=10),
        record("def-small-2", kind="def", source_lines=12),
        record("def-small-3", kind="def", source_lines=14),
        record("thm-small-1", kind="theorem", source_lines=10),
        record("thm-large-1", kind="theorem", source_lines=100),
        record("rejected", kind="theorem", source_lines=10),
    ]
    records[0]["chapter_id"] = None
    verdicts = {row["id"]: "provisionally_accept" for row in records}
    verdicts["rejected"] = "reject"

    selected = select_sample(
        records,
        verdicts,
        limit=10,
        max_per_stratum=2,
        selected_at="2026-04-28T00:00:00+00:00",
    )

    assert [row["id"] for row in selected] == [
        "def-small-1",
        "thm-large-1",
        "thm-small-1",
        "def-small-2",
    ]
    assert "rejected" not in {row["id"] for row in selected}
    assert [row["semantic_review_sample"]["rank"] for row in selected] == [1, 2, 3, 4]
    assert stratum_for_record(selected[0]) == "def:small"
