"""Tests for elaborated Lean dependency summaries."""

from scripts.analyze_lean_dependencies_elaborated import summarize


def test_summarize_accepts_latex_statement_gold_rows() -> None:
    records = [
        {
            "schema_version": "repoprover.latex_statement_unit.v1",
            "source_unit": {
                "environment": "lemma",
                "labels": ["lem.demo"],
            },
            "posthoc_lean_alignment": {
                "method": "lean_doc_comment_declared_label",
                "aligned_lean_declarations": [
                    {
                        "full_name": "Demo.foo",
                        "kind": "theorem",
                    },
                    {
                        "full_name": "Demo.bar",
                        "kind": "lemma",
                    },
                ],
            },
        }
    ]
    scan = {
        "Demo.foo": {
            "kind": "theorem",
            "used_mathlib": ["Nat.add_comm"],
            "used_mathlib_count": 1,
            "used_project": ["Demo.helper"],
            "used_other": [],
        },
        "Demo.bar": {
            "kind": "lemma",
            "used_mathlib": ["Finset.card"],
            "used_mathlib_count": 1,
            "used_project": [],
            "used_other": ["Eq"],
        },
    }

    summary = summarize(records, scan)

    assert summary["record_schema"] == "repoprover.latex_statement_unit.v1"
    assert summary["record_count"] == 1
    assert summary["missing_record_declarations"] == 0
    assert summary["global_unique"]["mathlib_direct_constants"] == 2
    assert summary["declarations_per_record"]["median"] == 2
    assert summary["per_exact_tex_label"]["labels"] == 1
    assert summary["per_exact_tex_label"]["records_per_label"]["median"] == 1
    assert summary["per_exact_tex_label"]["declarations_per_label"]["median"] == 2
    assert summary["per_exact_tex_label"]["mathlib_direct_constants"]["median"] == 2
