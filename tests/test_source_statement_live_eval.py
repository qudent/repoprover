"""Tests for target-statement-withheld source-statement eval prompts."""

from __future__ import annotations

import argparse
import copy
import json
import threading
import time
from pathlib import Path

from scripts.materialize_minimal_context_smoke import SelectedRecord
from scripts.run_source_statement_live_eval import build_messages, run, select_source_statement_records


def _write_fixture_project(tmp_path: Path) -> tuple[Path, SelectedRecord]:
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "Demo.lean").write_text(
        "\n".join(
            [
                "import Mathlib",
                "open scoped Matrix BigOperators",
                "open Finset Matrix",
                "",
                "namespace Demo",
                "",
                "variable {R : Type*} [CommRing R]",
                "",
                "/-- The submatrix helper used by the local notation. -/",
                "noncomputable def submatrixOfFinset {n m : Nat} (A : Matrix (Fin n) (Fin m) R)",
                "    (U : Finset (Fin n)) (V : Finset (Fin m)) :",
                "    Matrix (Fin U.card) (Fin V.card) R :=",
                "  A.submatrix (U.orderEmbOfFin rfl) (V.orderEmbOfFin rfl)",
                "",
                "/-- Notation for submatrices: `sub[U,V] A` denotes sub_U^V A. -/",
                'scoped notation "sub[" U "," V "] " A => submatrixOfFinset A U V',
                "",
                "/-- Local style example: use Mathlib's `.submatrix` API for diagonal principal minors. -/",
                "example {n : Nat} (d : Fin n -> R) (P : Finset (Fin n)) :",
                "    ((Matrix.diagonal d).submatrix (P.orderEmbOfFin rfl) (P.orderEmbOfFin rfl)).det =",
                "    ∏ i ∈ P, d i := by",
                "  sorry",
                "",
                "/-- Part (a): target declaration withheld in prompts.",
                "    Label: demo.minors.a -/",
                "theorem target {n : Nat} (d : Fin n -> R) (P : Finset (Fin n)) : True := by",
                "  trivial",
                "",
                "end Demo",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (project_root / "Demo.tex").write_text(
        "\\begin{lemma}\\label{demo.minors} Then: "
        "\\textbf{(a)} principal minors are products. "
        "\\textbf{(b)} off-diagonal minors vanish.\\end{lemma}\n",
        encoding="utf-8",
    )
    row = {
        "id": "Demo.lean:Demo.target",
        "alignment": {
            "comment_labels": ["demo.minors", "demo.minors.a"],
            "paired_source_path": "Demo.tex",
            "source_method": "lean_comment_label",
        },
        "output": {
            "lean_path": "Demo.lean",
            "declaration_names": ["Demo.target"],
            "line_range": [24, 26],
            "chunk_kind": "theorem",
        },
        "minimal_context": {
            "source_spans": [{"path": "Demo.tex", "line_range": [1, 1], "labels": ["demo.minors"]}],
            "file_context": [
                {"path": "Demo.lean", "kind": "open", "line_range": [2, 2], "name": "open scoped Matrix BigOperators"},
                {"path": "Demo.lean", "kind": "open", "line_range": [3, 3], "name": "open Finset Matrix"},
                {"path": "Demo.lean", "kind": "namespace", "line_range": [5, 5], "name": "Demo"},
                {"path": "Demo.lean", "kind": "variable", "line_range": [7, 7], "name": "variable {R : Type*} [CommRing R]"},
                {
                    "path": "Demo.lean",
                    "kind": "notation",
                    "line_range": [16, 16],
                    "name": 'scoped notation "sub[" U "," V "] " A => submatrixOfFinset A U V',
                },
            ],
            "lean_predecessors": [],
            "mathlib_context": ["Mathlib context"],
        },
    }
    return project_root, SelectedRecord(row)


def test_source_statement_prompt_includes_local_style_and_notation_contract(tmp_path: Path) -> None:
    project_root, record = _write_fixture_project(tmp_path)

    messages = build_messages(project_root, record)
    user = json.loads(messages[1]["content"])
    context = user["context"]
    local_style = context["local_lean_style"]
    guide = "\n".join(local_style["guidance"])
    examples = "\n".join(local_style["examples"])

    assert "sub[U,V] A" in guide
    assert "submatrixOfFinset A U V" in guide
    assert "do not cite or invent raw helper names" in guide
    assert "scoped notation" in examples
    assert "noncomputable def submatrixOfFinset" in examples
    assert "((Matrix.diagonal d).submatrix" in examples


def test_source_statement_prompt_focuses_specific_part_of_multipart_source(tmp_path: Path) -> None:
    project_root, record = _write_fixture_project(tmp_path)

    messages = build_messages(project_root, record)
    user = json.loads(messages[1]["content"])
    instructions = "\n".join(user["instructions"])
    focus = user["context"]["target_source_focus"]

    assert focus["specific_source_labels"] == ["demo.minors.a"]
    assert focus["specific_labeled_parts"] == ["a"]
    assert "formalize only the specified labeled part/source span" in instructions
    assert "Do not conjoin all parts" in instructions


def test_source_statement_prompt_includes_current_lean_environment_guidance(tmp_path: Path) -> None:
    project_root, record = _write_fixture_project(tmp_path)
    (project_root / "lean-toolchain").write_text("leanprover/lean4:v4.28.0\n", encoding="utf-8")

    messages = build_messages(project_root, record)
    system = messages[0]["content"]
    user = json.loads(messages[1]["content"])
    instructions = "\n".join(user["instructions"])
    environment = user["context"]["lean_environment"]
    guidance = "\n".join(environment["current_version_guidance"])

    assert "current Mathlib-only project" in system
    assert environment["toolchain"] == "leanprover/lean4:v4.28.0"
    assert "Lean 3" in guidance
    assert "LaurentPolynomial.X" in guidance
    assert "typeclass objects" in guidance
    assert "Use current Lean 4/Mathlib syntax" in instructions
    assert "do not bundle typeclass instances" in instructions


def _write_records(path: Path, row: dict, count: int) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for index in range(count):
            cloned = copy.deepcopy(row)
            cloned["id"] = f"Demo.lean:Demo.target{index}"
            cloned["output"]["declaration_names"] = [f"Demo.target{index}"]
            handle.write(json.dumps(cloned, ensure_ascii=False) + "\n")


def _run_args(project_root: Path, records: Path, output: Path, **overrides: object) -> argparse.Namespace:
    values = {
        "records": records,
        "project_root": project_root,
        "output": output,
        "limit": 4,
        "model": "test/model",
        "base_url": "https://example.invalid/api/v1",
        "max_tokens": 128,
        "temperature": 0.0,
        "reasoning_effort": None,
        "lake_cache_from": None,
        "lean_timeout": 1,
        "openrouter_timeout": 1.0,
        "max_actual_cost_usd": 2.0,
        "concurrency": 2,
        "sample_mode": "corpus-spread",
        "budget_only": False,
    }
    values.update(overrides)
    return argparse.Namespace(**values)


def _fake_response(content: str, *, finish_reason: str = "stop", cost: float = 0.0001) -> dict:
    return {
        "model": "test/model",
        "choices": [{"message": {"content": content}, "finish_reason": finish_reason}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30, "cost": cost},
    }


def test_source_statement_live_eval_runs_records_concurrently_and_writes_partials(
    tmp_path: Path, monkeypatch
) -> None:
    project_root, record = _write_fixture_project(tmp_path)
    records_path = tmp_path / "records.jsonl"
    _write_records(records_path, record.row, 4)

    active = 0
    max_active = 0
    lock = threading.Lock()

    def fake_call_openrouter(payload: dict, base_url: str, timeout: float) -> dict:
        nonlocal active, max_active
        with lock:
            active += 1
            max_active = max(max_active, active)
        time.sleep(0.05)
        with lock:
            active -= 1
        body = json.dumps(
            {
                "lean_declaration": "theorem generated : True := by\n  trivial",
                "declaration_name": "generated",
                "used_context": [],
                "notes": [],
            }
        )
        return _fake_response(body)

    monkeypatch.setattr("scripts.run_source_statement_live_eval.call_openrouter", fake_call_openrouter)
    monkeypatch.setattr(
        "scripts.run_source_statement_live_eval.run_lean",
        lambda project_root, target_path, timeout: {"exit_code": 0, "output": ""},
    )

    summary = run(_run_args(project_root, records_path, tmp_path / "out"))

    assert max_active == 2
    assert summary["records_attempted"] == 4
    assert summary["paid_calls_made"] == 4
    assert summary["successes"] == 4
    assert summary["failure_classes"] == {}
    partial_jsonl = tmp_path / "out/eval/partial-results.jsonl"
    assert len(partial_jsonl.read_text(encoding="utf-8").splitlines()) == 4


def test_source_statement_live_eval_enforces_global_estimated_cost_cap(
    tmp_path: Path, monkeypatch
) -> None:
    project_root, record = _write_fixture_project(tmp_path)
    records_path = tmp_path / "records.jsonl"
    _write_records(records_path, record.row, 2)

    def fail_call_openrouter(payload: dict, base_url: str, timeout: float) -> dict:
        raise AssertionError("cost-capped records must not call OpenRouter")

    monkeypatch.setattr("scripts.run_source_statement_live_eval.call_openrouter", fail_call_openrouter)

    summary = run(
        _run_args(
            project_root,
            records_path,
            tmp_path / "out",
            limit=2,
            max_tokens=32768,
            max_actual_cost_usd=0.00001,
        )
    )

    assert summary["records_attempted"] == 0
    assert summary["paid_calls_made"] == 0
    assert summary["failure_classes"] == {"skipped_cost_cap": 2}


def test_source_statement_live_eval_classifies_length_no_content(tmp_path: Path, monkeypatch) -> None:
    project_root, record = _write_fixture_project(tmp_path)
    records_path = tmp_path / "records.jsonl"
    _write_records(records_path, record.row, 1)

    monkeypatch.setattr(
        "scripts.run_source_statement_live_eval.call_openrouter",
        lambda payload, base_url, timeout: _fake_response("", finish_reason="length"),
    )

    summary = run(_run_args(project_root, records_path, tmp_path / "out", limit=1))

    assert summary["records_attempted"] == 1
    assert summary["failure_classes"] == {"no_content_or_length": 1}


def test_source_statement_sample_mode_easy_prefers_smaller_records() -> None:
    rows = []
    for index, (source_end, output_end, predecessor_count) in enumerate([(20, 7, 2), (3, 5, 0), (8, 4, 1)]):
        rows.append(
            {
                "id": f"r{index}",
                "output": {
                    "lean_path": "Demo.lean",
                    "declaration_names": [f"Demo.t{index}"],
                    "line_range": [4, output_end],
                    "chunk_kind": "theorem",
                },
                "minimal_context": {
                    "source_spans": [{"path": "Demo.tex", "line_range": [1, source_end]}],
                    "lean_predecessors": [{"declaration": f"p{n}"} for n in range(predecessor_count)],
                },
            }
        )

    selected = select_source_statement_records(rows, limit=2, sample_mode="easy")

    assert [item.selected.record_id for item in selected] == ["r1", "r2"]
