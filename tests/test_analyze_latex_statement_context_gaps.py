"""Tests for post-hoc theorem context-gap diagnostics."""

import json
from pathlib import Path

from scripts.analyze_latex_statement_context_gaps import analyze


def _write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def test_context_gap_detects_same_source_intermediate_dependency(tmp_path: Path) -> None:
    run = tmp_path / "run"
    batch = run / "batch-001"
    batch.mkdir(parents=True)
    _write_json(
        batch / "generation-payload.json",
        {
            "messages": [
                {"role": "system", "content": "demo"},
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "units": [
                                {
                                    "unit_key": "unit-001",
                                    "planned_declarations": [
                                        {
                                            "hydrated_mathlib_context": [
                                                {
                                                    "exact_identifier": "Mathlib.used",
                                                    "lean_check": {"status": "checked"},
                                                }
                                            ],
                                            "available_prior_project_context": [],
                                            "local_file_predecessor_declarations": [
                                                {"name": "Prior.helper"}
                                            ],
                                        }
                                    ],
                                }
                            ]
                        }
                    ),
                },
            ]
        },
    )
    failure_summary = tmp_path / "failure.json"
    _write_json(
        failure_summary,
        {
            "best_sources": [
                {
                    "source_unit_id": "source:one",
                    "best_run": str(run),
                    "unit_key": "unit-001",
                    "failure_class": "declined_cannot_prove",
                    "error_pattern": "declined_cannot_prove",
                }
            ]
        },
    )
    gold = tmp_path / "gold.jsonl"
    gold.write_text(
        json.dumps(
            {
                "id": "source:one",
                "posthoc_lean_alignment": {
                    "aligned_lean_declarations": [{"full_name": "Target.main"}],
                    "referencing_lean_declarations": [{"full_name": "Target.sameSourceHelper"}],
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )
    scan = tmp_path / "scan.jsonl"
    scan.write_text(
        json.dumps(
            {
                "declaration": "Target.main",
                "used_mathlib": ["Mathlib.used"],
                "used_project": ["Target.sameSourceHelper"],
                "used_other": [],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    summary = analyze(failure_summary=failure_summary, gold_candidates=gold, scan_jsonl=scan)

    row = summary["sources"][0]
    assert row["gap_class"] == "gold_uses_same_source_intermediate_declarations"
    assert row["overlap"]["mathlib"]["exact_overlap"] == ["Mathlib.used"]
    assert row["overlap"]["project"]["gold_missing_exact_sample"] == ["Target.sameSourceHelper"]


def test_context_gap_reads_repair_checked_context(tmp_path: Path) -> None:
    run = tmp_path / "repair"
    batch = run / "batch-001"
    batch.mkdir(parents=True)
    _write_json(
        batch / "generation-payload.json",
        {
            "messages": [
                {"role": "system", "content": "demo"},
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "original_generation_task": {
                                "units": [
                                    {
                                        "unit_key": "unit-001",
                                        "planned_declarations": [
                                            {
                                                "hydrated_mathlib_context": [],
                                                "available_prior_project_context": [],
                                                "local_file_predecessor_declarations": [],
                                            }
                                        ],
                                    }
                                ]
                            },
                            "additional_checked_repair_context": [
                                {
                                    "checked_signatures": [
                                        {
                                            "unit_key": "unit-001",
                                            "name": "Gold.mathlib",
                                        }
                                    ]
                                }
                            ],
                        }
                    ),
                },
            ]
        },
    )
    failure_summary = tmp_path / "failure.json"
    _write_json(
        failure_summary,
        {
            "best_sources": [
                {
                    "source_unit_id": "source:one",
                    "best_run": str(run),
                    "unit_key": "unit-001",
                    "failure_class": "declined_cannot_prove",
                }
            ]
        },
    )
    gold = tmp_path / "gold.jsonl"
    gold.write_text(
        json.dumps(
            {
                "id": "source:one",
                "posthoc_lean_alignment": {
                    "aligned_lean_declarations": [{"full_name": "Target.main"}],
                    "referencing_lean_declarations": [],
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )
    scan = tmp_path / "scan.jsonl"
    scan.write_text(
        json.dumps(
            {
                "declaration": "Target.main",
                "used_mathlib": ["Gold.mathlib"],
                "used_project": [],
                "used_other": [],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    summary = analyze(failure_summary=failure_summary, gold_candidates=gold, scan_jsonl=scan)

    row = summary["sources"][0]
    assert row["selected_context"]["repair_checked_names"] == ["Gold.mathlib"]
    assert row["gap_class"] == "generator_declined_despite_direct_dependency_overlap"
