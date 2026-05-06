"""Tests for theorem-level failure taxonomy summaries."""

import json
from pathlib import Path

from scripts.summarize_latex_statement_failures import summarize_roots


def test_summarize_roots_infers_old_failure_classes(tmp_path: Path) -> None:
    run = tmp_path / "runs/demo"
    selector = tmp_path / "selector"
    eval_dir = run / "eval"
    eval_dir.mkdir(parents=True)
    (selector / "eval").mkdir(parents=True)
    (selector / "eval/selected-units.jsonl").write_text(
        "\n".join(
            json.dumps({"id": source_id})
            for source_id in ["source:one", "source:two", "source:three"]
        )
        + "\n",
        encoding="utf-8",
    )
    (eval_dir / "generation-results.json").write_text(
        json.dumps({"selector_run": str(selector)}),
        encoding="utf-8",
    )
    (eval_dir / "verification-results.json").write_text(
        json.dumps(
            {
                "batches": [
                    {
                        "units": [
                            {
                                "unit_key": "unit-001",
                                "compile_passed": True,
                                "contract_violations": [],
                                "lean_returncode": 0,
                                "lean_error_count": 0,
                            },
                            {
                                "unit_key": "unit-002",
                                "reported_status": "cannot_prove_from_visible_context",
                                "compile_passed": False,
                                "contract_violations": [],
                                "lean_returncode": None,
                                "lean_error_count": 0,
                                "skipped_reason": "cannot_prove_from_visible_context",
                            },
                            {
                                "unit_key": "unit-003",
                                "reported_status": "generated",
                                "compile_passed": False,
                                "contract_violations": ["generated_lean_contains_placeholder"],
                                "lean_returncode": 0,
                                "lean_error_count": 0,
                            },
                        ]
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    (eval_dir / "gold-comparison.json").write_text(
        json.dumps({"coverage_status_counts": {"compiled_needs_semantic_review": 1}}),
        encoding="utf-8",
    )

    summary = summarize_roots([tmp_path / "runs"], max_examples_per_class=2)

    assert summary["verification_result_count"] == 1
    assert summary["unit_count"] == 3
    assert summary["compile_passed_units"] == 1
    assert summary["failure_class_counts"] == {
        "compiled": 1,
        "contract_violation": 1,
        "declined_cannot_prove": 1,
    }
    assert summary["error_pattern_counts"] == {
        "compiled": 1,
        "contract_violation": 1,
        "declined_cannot_prove": 1,
    }
    assert summary["source_unit_count"] == 3
    assert summary["best_source_failure_class_counts"] == {
        "compiled": 1,
        "contract_violation": 1,
        "declined_cannot_prove": 1,
    }
    assert summary["coverage_status_counts"] == {"compiled_needs_semantic_review": 1}
    example = summary["examples_by_class"]["declined_cannot_prove"][0]
    assert example["unit_key"] == "unit-002"
    assert example["source_unit_id"] == "source:two"


def test_summarize_roots_uses_best_observed_source_status(tmp_path: Path) -> None:
    selector = tmp_path / "selector"
    (selector / "eval").mkdir(parents=True)
    (selector / "eval/selected-units.jsonl").write_text(
        json.dumps({"id": "source:shared"}) + "\n",
        encoding="utf-8",
    )
    failed = tmp_path / "runs/failed/eval"
    passed = tmp_path / "runs/passed/eval"
    failed.mkdir(parents=True)
    passed.mkdir(parents=True)
    for eval_dir, compile_passed, returncode in [(failed, False, 1), (passed, True, 0)]:
        (eval_dir / "generation-results.json").write_text(
            json.dumps({"selector_run": str(selector)}),
            encoding="utf-8",
        )
        (eval_dir / "verification-results.json").write_text(
            json.dumps(
                {
                    "batches": [
                        {
                            "units": [
                                {
                                    "unit_key": "unit-001",
                                    "compile_passed": compile_passed,
                                    "contract_violations": [],
                                    "lean_returncode": returncode,
                                    "lean_error_count": 0 if compile_passed else 1,
                                }
                            ]
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )

    summary = summarize_roots([tmp_path / "runs"], max_examples_per_class=2)

    assert summary["failure_class_counts"] == {"compile_failure": 1, "compiled": 1}
    assert summary["source_unit_count"] == 1
    assert summary["best_source_failure_class_counts"] == {"compiled": 1}
    assert summary["best_sources"][0]["source_unit_id"] == "source:shared"
    assert summary["best_sources"][0]["failure_class"] == "compiled"


def test_summarize_roots_accepts_direct_verification_file(tmp_path: Path) -> None:
    path = tmp_path / "verification-results.json"
    path.write_text(
        json.dumps(
            {
                "batches": [
                    {
                        "units": [
                            {
                                "unit_key": "unit-001",
                                "failure_class": "compile_failure",
                                "compile_passed": False,
                                "lean_returncode": 1,
                                "lean_error_count": 1,
                                "messages": [
                                    {
                                        "severity": "error",
                                        "data": "Unknown constant `Demo.missing`",
                                    }
                                ],
                            }
                        ]
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    summary = summarize_roots([path], max_examples_per_class=1)

    assert summary["verification_result_count"] == 1
    assert summary["failure_class_counts"] == {"compile_failure": 1}
    assert summary["error_pattern_counts"] == {"unknown_constant": 1}
    assert summary["examples_by_class"]["compile_failure"][0]["error_pattern"] == "unknown_constant"
    assert summary["examples_by_class"]["compile_failure"][0]["first_error"] == "Unknown constant `Demo.missing`"
