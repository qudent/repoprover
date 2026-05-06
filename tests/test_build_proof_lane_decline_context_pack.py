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


def test_dependency_closure_adds_visible_project_dependencies(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    source = project_root / "Project/Safe.lean"
    source.parent.mkdir(parents=True)
    source.write_text(
        "\n".join(
            [
                "import Mathlib",
                "",
                "namespace Project",
                "",
                "variable {K : Type*} [CommRing K]",
                "",
                "def helper : K := 0",
                "",
                "def safeDef : K := helper",
                "",
                "theorem hiddenTarget : True := by trivial",
                "",
                "end Project",
            ]
        ),
        encoding="utf-8",
    )
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
            "project_root": str(project_root),
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
                                    "line": 9,
                                    "snippet": "def safeDef : K := helper",
                                    "match_kind": "exact_local_name",
                                }
                            ],
                        }
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
                            "full_name": "Project.hiddenTarget",
                            "path": "Project/Safe.lean",
                            "line_range": [11, 11],
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
            project_root=project_root,
            max_candidates_per_identifier=3,
            dependency_depth=1,
            max_dependencies_per_unit=8,
        )
    )

    unit = pack["units"][0]
    names = [row["name"] for row in unit["selected_project_context"]]
    assert names == [
        "Project.safeDef",
        "Project.helper",
        "variable {K : Type*} [CommRing K]",
    ]
    assert unit["dependency_project_context_count"] == 1
    assert "Project.hiddenTarget" not in json.dumps(pack)


def test_dependency_closure_skips_ambiguous_one_letter_dependencies(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    source = project_root / "Project/Safe.lean"
    source.parent.mkdir(parents=True)
    source.write_text(
        "\n".join(
            [
                "namespace Project",
                "",
                "def x : Nat := 0",
                "",
                "def safeDef : Nat := x",
                "",
                "end Project",
            ]
        ),
        encoding="utf-8",
    )
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
            "project_root": str(project_root),
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
                                    "line": 5,
                                    "snippet": "def safeDef : Nat := x",
                                    "match_kind": "exact_local_name",
                                }
                            ],
                        }
                    ],
                }
            ],
        },
    )
    gold = tmp_path / "gold.jsonl"
    _write_jsonl(gold, [{"id": "tex/file.tex:thm.demo", "posthoc_lean_alignment": {}}])

    pack = build_pack(
        argparse.Namespace(
            decline_context_report=decline_report,
            gold_candidates=gold,
            project_root=project_root,
            max_candidates_per_identifier=3,
            dependency_depth=1,
            max_dependencies_per_unit=8,
        )
    )

    names = [row["name"] for row in pack["units"][0]["selected_project_context"]]
    assert names == ["Project.safeDef"]


def test_dependency_closure_keeps_same_file_field_dependencies(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    source = project_root / "Project/Safe.lean"
    source.parent.mkdir(parents=True)
    source.write_text(
        "\n".join(
            [
                "namespace Project",
                "",
                "def finish : Nat := 0",
                "",
                "def safeDef : Nat := p.finish + vertices.length",
                "",
                "end Project",
                "",
                "namespace Other",
                "def length : Nat := 0",
                "end Other",
            ]
        ),
        encoding="utf-8",
    )
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
            "project_root": str(project_root),
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
                                        "path": str(source),
                                        "line": 5,
                                        "snippet": "def safeDef : Nat := p.finish + vertices.length",
                                        "match_kind": "exact_local_name",
                                }
                            ],
                        }
                    ],
                }
            ],
        },
    )
    gold = tmp_path / "gold.jsonl"
    _write_jsonl(gold, [{"id": "tex/file.tex:thm.demo", "posthoc_lean_alignment": {}}])

    pack = build_pack(
        argparse.Namespace(
            decline_context_report=decline_report,
            gold_candidates=gold,
            project_root=project_root,
            max_candidates_per_identifier=3,
            dependency_depth=1,
            max_dependencies_per_unit=8,
        )
    )

    names = [row["name"] for row in pack["units"][0]["selected_project_context"]]
    assert names == ["Project.safeDef", "Project.finish"]
