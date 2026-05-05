"""Tests for theorem-level Mathlib context hydration."""

from scripts.hydrate_latex_statement_context import build_check_source, hydrate_output, iter_mathlib_requests


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
