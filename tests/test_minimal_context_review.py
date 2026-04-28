"""Tests for minimal-context review helpers."""

from __future__ import annotations

from scripts.review_minimal_context_records import (
    extract_declaration_hits,
    extract_json_object,
    numbered_snippet,
)
from scripts.generate_minimal_context_records import (
    ReviewUsage,
    chunk_declarations,
    normalize_model_record,
    parse_lean_declarations,
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


def test_parse_lean_declarations_includes_doc_comments_and_attributes() -> None:
    lean_text = "\n".join(
        [
            "namespace Demo",
            "",
            "/-- A target theorem. -/",
            "@[simp]",
            "theorem target : True := by",
            "  trivial",
            "",
            "private lemma hidden : True := by",
            "  trivial",
            "private lemma hidden' : True := by",
            "  trivial",
            "",
            "/-- Another theorem. -/",
            "noncomputable def other : Nat := 1",
            "end Demo",
        ]
    )

    declarations = parse_lean_declarations(lean_text)

    assert [decl.full_name for decl in declarations] == ["Demo.target", "Demo.other"]
    assert declarations[0].start_line == 3
    assert declarations[0].end_line == 6
    assert declarations[1].kind == "def"

    private_declarations = parse_lean_declarations(lean_text, include_private=True)

    assert any(decl.full_name == "Demo.hidden'" for decl in private_declarations)


def test_chunk_declarations_preserves_known_output_range() -> None:
    lean_text = "\n".join(
        [
            "namespace Demo",
            "/-- First. -/",
            "theorem first : True := by",
            "  trivial",
            "/-- Second. -/",
            "theorem second : True := by",
            "  trivial",
            "end Demo",
        ]
    )
    declarations = parse_lean_declarations(lean_text)

    chunks = chunk_declarations(declarations, lean_text, chunk_size=2)

    assert chunks[0].declaration_names == ["Demo.first", "Demo.second"]
    assert chunks[0].start_line == 2
    assert chunks[0].end_line == 7


def test_normalize_model_record_embeds_generation_and_tex_only_fields() -> None:
    lean_text = "\n".join(["namespace Demo", "/-- First. -/", "theorem first : True := by", "  trivial"])
    candidate = chunk_declarations(parse_lean_declarations(lean_text), lean_text, chunk_size=1)[0]

    row = normalize_model_record(
        model_record={
            "record_suffix": "first",
            "chunk_kind": "theorem",
            "source_spans": [{"path": "Demo.tex", "line_range": [2, 4], "labels": ["demo"]}],
            "imports": ["Mathlib"],
            "tex_only_inferability": {
                "score": 0.4,
                "assessment": "TeX gives the statement but not the proof API.",
                "missing_from_tex_only": ["True.intro"],
            },
            "trust": {"source_span": 1.0, "lean_dependency_graph": 1.0, "model_extraction": 1.0},
        },
        candidate=candidate,
        chapter_id="demo",
        lean_path="Demo.lean",
        tex_path="Demo.tex",
        model="model/id",
        source_base_url="https://example.test",
        usage=ReviewUsage(prompt_tokens=10, completion_tokens=5, cost_usd=0.001),
        elapsed_seconds=1.23456,
        generated_at="2026-04-28T00:00:00+00:00",
        raw_response='{"record_suffix":"first"}',
    )

    assert row["id"] == "demo:first"
    assert row["tex_only_inferability"]["score"] == 0.4
    assert row["trust"] == {
        "source_span": 0.65,
        "lean_dependency_graph": 0.55,
        "model_extraction": 0.45,
        "human_review": 0.0,
    }
    assert "trust capped" in " ".join(row["review_notes"])
    assert row["generation"]["prompt_tokens"] == 10
    assert row["generation"]["estimated_cost_usd"] == 0.001


def test_normalize_model_record_splits_local_predecessors_from_mathlib_context() -> None:
    lean_text = "\n".join(
        [
            "namespace Demo",
            "lemma helper' : True := by",
            "  trivial",
            "theorem target : True := by",
            "  exact helper'",
        ]
    )
    declarations = parse_lean_declarations(lean_text)
    candidate = chunk_declarations([declarations[1]], lean_text, chunk_size=1)[0]

    row = normalize_model_record(
        model_record={
            "record_suffix": "target",
            "lean_predecessors": [{"declaration": "helper", "reason": "used in proof"}],
            "mathlib_context": ["helper", "True.intro"],
        },
        candidate=candidate,
        chapter_id="demo",
        lean_path="Demo.lean",
        tex_path="Demo.tex",
        model="model/id",
        source_base_url="https://example.test",
        usage=ReviewUsage(prompt_tokens=1, completion_tokens=1, cost_usd=0.0),
        elapsed_seconds=0.1,
        generated_at="2026-04-28T00:00:00+00:00",
        raw_response="{}",
        local_declarations={declarations[0].full_name: declarations[0]},
    )

    assert row["minimal_context"]["lean_predecessors"] == [
        {"path": "Demo.lean", "declaration": "Demo.helper'", "reason": "used in proof"}
    ]
    assert row["minimal_context"]["mathlib_context"] == ["True.intro"]


def test_normalize_model_record_strips_local_namespace_from_mathlib_context() -> None:
    lean_text = "\n".join(["namespace Demo", "theorem target : True := by", "  trivial"])
    candidate = chunk_declarations(parse_lean_declarations(lean_text), lean_text, chunk_size=1)[0]

    row = normalize_model_record(
        model_record={"record_suffix": "target", "mathlib_context": ["Demo.True.intro"]},
        candidate=candidate,
        chapter_id="demo",
        lean_path="Demo.lean",
        tex_path="Demo.tex",
        model="model/id",
        source_base_url="https://example.test",
        usage=ReviewUsage(prompt_tokens=1, completion_tokens=1, cost_usd=0.0),
        elapsed_seconds=0.1,
        generated_at="2026-04-28T00:00:00+00:00",
        raw_response="{}",
    )

    assert row["minimal_context"]["mathlib_context"] == ["True.intro"]
