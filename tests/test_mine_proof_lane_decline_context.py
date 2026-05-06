"""Tests for source-only proof-lane decline context mining."""

import argparse
import json
from pathlib import Path

from scripts.mine_proof_lane_decline_context import analyze, parse_project_declarations


def _write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def test_mines_found_selected_and_missing_identifiers(tmp_path: Path) -> None:
    project = tmp_path / "project"
    lean_file = project / "Project/Foo.lean"
    lean_file.parent.mkdir(parents=True)
    lean_file.write_text(
        "\n".join(
            [
                "namespace Project",
                "",
                "def missingFoo : Nat := 0",
                "",
                "lemma selectedLemma : missingFoo = 0 := by rfl",
                "",
                "namespace Bar",
                "",
                "theorem bazThing : True := by trivial",
                "",
                "end Bar",
                "end Project",
            ]
        ),
        encoding="utf-8",
    )

    task_dir = tmp_path / "tasks"
    _write_json(
        task_dir / "tasks/unit-001.json",
        {
            "unit_key": "unit-001",
            "current_generation": {"notes": ["Prior model note mentioned missingFoo but did not include the declaration."]},
            "visible_prompt_context": {
                "planned_declarations": [
                    {
                        "available_prior_project_context": [
                            {
                                "project_declarations": [
                                    {"name": "Project.selectedLemma", "lean_snippet": "lemma selectedLemma"}
                                ]
                            }
                        ],
                        "local_file_predecessor_declarations": [],
                        "hydrated_mathlib_context": [],
                    }
                ]
            },
        },
    )

    run_dir = tmp_path / "run"
    _write_json(
        run_dir / "eval/generation-results.json",
        {"proof_lane_task_dir": str(task_dir)},
    )
    _write_json(
        run_dir / "eval/merged-generation-output.json",
        {
            "units": [
                {
                    "unit_key": "unit-001",
                    "status": "cannot_prove_from_visible_context",
                    "notes": [
                        "Missing definitions: missingFoo, Project.Bar.bazThing, absentFact. "
                        "The helper selectedLemma is visible."
                    ],
                }
            ]
        },
    )

    summary = analyze(
        argparse.Namespace(
            proof_lane_generation_run=[run_dir],
            proof_lane_task_dir=None,
            project_root=project,
            unit_key=None,
            max_candidates=4,
        )
    )

    results = {
        result["identifier"]: result
        for result in summary["units"][0]["identifier_results"]
    }
    assert results["missingFoo"]["classification"] == "found_and_name_mentioned_but_declaration_not_selected"
    assert results["missingFoo"]["candidates"][0]["name"] == "Project.missingFoo"
    assert results["Project.Bar.bazThing"]["classification"] == "found_but_not_visible"
    assert results["selectedLemma"]["classification"] == "found_and_selected_as_visible_context"
    assert results["absentFact"]["classification"] == "not_found_in_project_index"


def test_parse_project_declarations_prefixes_dotted_names_inside_namespace(tmp_path: Path) -> None:
    project = tmp_path / "project"
    lean_file = project / "Project/Foo.lean"
    lean_file.parent.mkdir(parents=True)
    lean_file.write_text(
        "\n".join(
            [
                "namespace Project",
                "inductive Step where",
                "  | east",
                "def Step.apply : Step -> Nat",
                "  | Step.east => 1",
                "def _root_.Global.helper : Nat := 2",
                "end Project",
            ]
        ),
        encoding="utf-8",
    )

    by_name = {declaration.full_name: declaration for declaration in parse_project_declarations(project)}

    assert "Project.Step" in by_name
    assert "Project.Step.apply" in by_name
    assert "Global.helper" in by_name
