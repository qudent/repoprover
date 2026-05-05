"""Tests for theorem-level Mathlib context hydration."""

from scripts.hydrate_latex_statement_context import (
    build_check_source,
    fallback_mathlib_candidates,
    hydrate_output,
    iter_mathlib_requests,
    split_exact_identifier_list,
)


def _selector_output() -> dict:
    return {
        "units": [
            {
                "unit_key": "unit-001",
                "planned_declarations": [
                    {
                        "task_id": "unit-001-task-1",
                        "source_part": "whole unit",
                        "needed_mathlib_context": [
                            {
                                "name_or_query": "Nat.add_comm",
                                "expected_signature_or_shape": "a + b = b + a",
                                "why_needed": "commute addition",
                            },
                            {
                                "name_or_query": "PowerSeries coefficient theorem",
                                "expected_signature_or_shape": "coeff n f",
                                "why_needed": "narrow search fallback",
                            },
                        ],
                    }
                ],
            }
        ]
    }


def test_iter_mathlib_requests_extracts_exact_and_query_items() -> None:
    requests = iter_mathlib_requests(_selector_output())

    assert [request.query for request in requests] == ["Nat.add_comm", "PowerSeries coefficient theorem"]
    assert requests[0].exact_identifier == "Nat.add_comm"
    assert requests[1].exact_identifier is None
    assert requests[0].expected_signature_or_shape == "a + b = b + a"


def test_build_check_source_maps_check_lines() -> None:
    source, line_to_name = build_check_source(
        ["Nat.add_comm", "IsUnit"],
        imports=["Mathlib"],
        opens=["open PowerSeries"],
    )

    assert "#check Nat.add_comm" in source
    assert line_to_name == {3: "Nat.add_comm", 4: "IsUnit"}


def test_split_exact_identifier_list() -> None:
    assert split_exact_identifier_list("mul_assoc, one_mul, mul_one") == [
        "mul_assoc",
        "one_mul",
        "mul_one",
    ]
    assert split_exact_identifier_list("PowerSeries coefficient theorem") == []


def test_hydrate_output_marks_non_exact_queries(monkeypatch, tmp_path) -> None:
    def fake_check_names(names, *, project_root, imports, opens, timeout_seconds):
        return {
            "status": "ok",
            "checked": {
                "Nat.add_comm": {
                    "status": "checked",
                    "signature": "Nat.add_comm (n m : Nat) : n + m = m + n",
                }
            },
        }

    monkeypatch.setattr("scripts.hydrate_latex_statement_context.lean_check_names", fake_check_names)

    hydrated = hydrate_output(
        _selector_output(),
        project_root=tmp_path,
        imports=["Mathlib"],
        opens=[],
        timeout_seconds=1,
    )

    assert hydrated["request_count"] == 2
    assert hydrated["exact_identifier_count"] == 1
    assert hydrated["hydrated_mathlib_context"][0]["lean_check"]["status"] == "checked"
    assert hydrated["hydrated_mathlib_context"][1]["lean_check"]["status"] == "not_exact_identifier"


def test_fallback_mathlib_candidates_scores_local_mathlib_declarations(tmp_path) -> None:
    mathlib_file = tmp_path / ".lake/packages/mathlib/Mathlib/Demo/Symmetric.lean"
    mathlib_file.parent.mkdir(parents=True)
    mathlib_file.write_text(
        "\n".join(
            [
                "namespace MvPolynomial",
                "section CommSemiring",
                "end CommSemiring",
                "theorem esymm_eq_sum_subtype (n : Nat) : True := by trivial",
                "theorem unrelated : True := by trivial",
                "end MvPolynomial",
            ]
        ),
        encoding="utf-8",
    )

    candidates = fallback_mathlib_candidates("MvPolynomial.esymm_eq_zero_of_lt", project_root=tmp_path)

    assert candidates[0]["name"] == "MvPolynomial.esymm_eq_sum_subtype"
    assert "esymm" in candidates[0]["matched_tokens"]
