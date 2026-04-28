"""Tests for minimal-context review helpers."""

from __future__ import annotations

from scripts.review_minimal_context_records import (
    extract_declaration_hits,
    extract_json_object,
    numbered_snippet,
)


def test_numbered_snippet_uses_one_indexed_line_numbers() -> None:
    text = "alpha\nbeta\ngamma\ndelta"

    assert numbered_snippet(text, 2, 3) == "2: beta\n3: gamma"


def test_extract_declaration_hits_clips_to_declared_output_range() -> None:
    lean_text = "\n".join(
        [
            "theorem first : True := by",
            "  trivial",
            "",
            "theorem target : True := by",
            "  trivial",
            "",
            "theorem leaked_neighbor : True := by",
            "  trivial",
        ]
    )

    hits = extract_declaration_hits(lean_text, ["Example.target"], max_line=5)

    assert hits[0]["line"] == 4
    assert "target" in hits[0]["snippet"]
    assert "leaked_neighbor" not in hits[0]["snippet"]


def test_extract_json_object_accepts_fenced_json() -> None:
    parsed = extract_json_object('```json\n{"verdict": "revise"}\n```')

    assert parsed == {"verdict": "revise"}
