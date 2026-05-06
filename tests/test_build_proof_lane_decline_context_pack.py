"""Tests for prompt-safe proof-lane decline context packs."""

import argparse
import json
from pathlib import Path

from scripts.build_proof_lane_decline_context_pack import build_pack


def _write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n", encoding="utf-8")


def test_builds_pack_and_filters_same_source_hidden_declarations(tmp_path: Path) -> None:
    task_dir = tmp_path / "tasks"
    run_dir = tmp_path / "run"
    _write_json(run_dir / "eval/generation-results.json", {"proof_lane_task_dir": str(task_dir)})
    _write_json(
        task_dir / "tasks/unit-001.json",
        {
            "unit_key": "unit-001",
            "source_unit": {"id": "tex/file.tex:thm.demo", "labels": ["thm.demo"]},
        },
    )
    decline_report = tmp_path / "decline.json"
    _write_json(
        decline_report,
        {
            "project_root": "project",
            "units": [
                {
                    "run_dir": str(run_dir),
                    "unit_key": "unit-001",
                    "identifier_results": [
                        {
                            "identifier": "safeDef",
                            "classification": "found_and_name_mentioned_but_declaration_not_selected",
                            "candidates": [
                                {
                                    "name": "Project.safeDef",
                                    "kind": "def",
                                    "path": "project/Project/Safe.lean",
                                    "line": 10,
                                    "snippet": "def safeDef : Nat := 0",
                                    "match_kind": "exact_local_name",
                                }
                            ],
                        },
                        {
                            "identifier": "targetTheorem",
                            "classification": "found_and_name_mentioned_but_declaration_not_selected",
                            "candidates": [
                                {
                                    "name": "Project.targetTheorem",
                                    "kind": "theorem",
                                    "path": "project/Project/Target.lean",
                                    "line": 20,
                                    "snippet": "theorem targetTheorem : True := by trivial",
                                    "match_kind": "exact_local_name",
                                }
                            ],
                        },
                    ],
                }
            ],
        },
    )
    gold = tmp_path / "gold.jsonl"
    _write_jsonl(
        gold,
        [
            {
                "id": "tex/file.tex:thm.demo",
                "posthoc_lean_alignment": {
                    "aligned_lean_declarations": [
                        {
                            "full_name": "Project.targetTheorem",
                            "path": "Project/Target.lean",
                            "line_range": [20, 30],
                        }
                    ],
                    "referencing_lean_declarations": [],
                },
            }
        ],
    )

    pack = build_pack(
        argparse.Namespace(
            decline_context_report=decline_report,
            gold_candidates=gold,
            max_candidates_per_identifier=3,
        )
    )

    unit = pack["units"][0]
    assert unit["selected_project_context_count"] == 1
    assert unit["selected_project_context"][0]["name"] == "Project.safeDef"
    assert unit["excluded_hidden_candidate_count"] == 1
    assert "Project.targetTheorem" not in json.dumps(pack)
