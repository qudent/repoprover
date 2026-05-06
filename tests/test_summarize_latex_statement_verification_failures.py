"""Tests for theorem-level verification failure summaries."""

import json
from pathlib import Path

from scripts.summarize_latex_statement_verification_failures import render_markdown, summarize_one


def test_summarize_one_counts_failures_and_support(tmp_path: Path) -> None:
    path = tmp_path / "verification-results.json"
    path.write_text(
        json.dumps(
            {
                "generation_run": "run/root",
                "compile_passed_units": 1,
                "lean_call_count": 5,
                "lean_elapsed_seconds": 42.5,
                "batches": [
                    {
                        "units": [
                            {
                                "unit_key": "unit-001",
                                "reported_status": "generated",
                                "failure_class": "compiled",
                                "compile_passed": True,
                                "lean_error_count": 0,
                                "visible_support_context": {
                                    "candidate_count": 2,
                                    "accepted_count": 1,
                                    "rejected_count": 1,
                                    "skipped_count": 0,
                                    "lean_call_count": 2,
                                    "elapsed_seconds": 10.0,
                                },
                            },
                            {
                                "unit_key": "unit-002",
                                "reported_status": "generated",
                                "failure_class": "compile_failure",
                                "compile_passed": False,
                                "lean_error_count": 1,
                                "contract_violations": ["generated_lean_contains_placeholder"],
                                "placeholder_tokens": ["sorry"],
                                "messages": [
                                    {
                                        "severity": "error",
                                        "kind": "lean.unknownIdentifier",
                                        "data": "Unknown constant `Demo.missing`\nextra detail",
                                    }
                                ],
                                "visible_support_context": {
                                    "candidate_count": 3,
                                    "accepted_count": 2,
                                    "rejected_count": 1,
                                    "skipped_count": 0,
                                    "lean_call_count": 3,
                                    "elapsed_seconds": 12.0,
                                    "rejected": [
                                        {
                                            "messages": [
                                                {
                                                    "severity": "error",
                                                    "kind": "lean.unknownIdentifier",
                                                    "data": "Unknown identifier `Support.missing`",
                                                }
                                            ]
                                        }
                                    ],
                                },
                            },
                        ]
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    summary = summarize_one(path)

    assert summary["failure_class_counts"] == {"compile_failure": 1, "compiled": 1}
    assert summary["contract_violation_counts"] == {"generated_lean_contains_placeholder": 1}
    assert summary["placeholder_token_counts"] == {"sorry": 1}
    assert summary["route_counts"] == {"compiled": 1, "contract_violation": 1}
    assert summary["support_rejection_route_counts"] == {"missing_context_or_api": 1}
    assert summary["lean_error_signature_counts"] == {"Unknown constant `Demo.missing`": 1}
    assert summary["support_totals"] == {
        "accepted_count": 3,
        "candidate_count": 5,
        "elapsed_seconds": 22.0,
        "lean_call_count": 5,
        "rejected_count": 2,
        "skipped_count": 0,
    }


def test_render_markdown_includes_unit_rows(tmp_path: Path) -> None:
    report = {
        "generated_at": "2026-05-06T00:00:00Z",
        "runs": [
            {
                "generation_run": "run/root",
                "verification_results": "run/eval/verification-results.json",
                "unit_count": 1,
                "compile_passed_units": 0,
                "failure_class_counts": {"declined_cannot_prove": 1},
                "reported_status_counts": {"cannot_prove_from_visible_context": 1},
                "contract_violation_counts": {},
                "placeholder_token_counts": {},
                "route_counts": {"clean_decline": 1},
                "support_rejection_route_counts": {},
                "support_totals": {
                    "candidate_count": 0,
                    "accepted_count": 0,
                    "rejected_count": 0,
                    "skipped_count": 0,
                    "lean_call_count": 0,
                    "elapsed_seconds": 0.0,
                },
                "lean_call_count": 0,
                "lean_elapsed_seconds": 0.0,
                "lean_error_signature_counts": {},
                "units": [
                    {
                        "unit_key": "unit-001",
                        "failure_class": "declined_cannot_prove",
                        "reported_status": "cannot_prove_from_visible_context",
                        "lean_error_count": 0,
                        "routes": ["clean_decline"],
                        "support": {"accepted_count": 0, "candidate_count": 0},
                    }
                ],
            }
        ],
    }

    markdown = render_markdown(report)

    assert "run/root" in markdown
    assert "`unit-001` declined_cannot_prove" in markdown
    assert "Route counts" in markdown
    assert "routes=clean_decline" in markdown
