"""Tests for target-statement-withheld source-statement eval prompts."""

from __future__ import annotations

import argparse
import copy
import json
import threading
import time
from pathlib import Path

from scripts.materialize_minimal_context_smoke import SelectedRecord
from scripts.run_source_statement_live_eval import (
    build_messages,
    build_repair_messages,
    classify_lean_failure,
    copy_local_import_closure,
    generated_application_candidates,
    import_modules_from_lean,
    local_import_path,
    materialize_candidate_project,
    run,
    select_source_statement_records,
)


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
    assert "theorem target" not in examples


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


def test_repair_prompt_uses_generated_only_error_without_grader_feedback(tmp_path: Path) -> None:
    project_root, record = _write_fixture_project(tmp_path)
    messages = build_messages(project_root, record)

    repair_messages = build_repair_messages(
        original_messages=messages,
        failed_declaration="theorem bad : True := by\n  exact missingFact",
        generated_only_lean_result={"exit_code": 1, "output": "unknown identifier 'missingFact'"},
    )
    system = repair_messages[0]["content"]
    user = json.loads(repair_messages[1]["content"])
    prompt_text = json.dumps(user, ensure_ascii=False)

    assert "target Lean statement and target declaration name are still withheld" in system
    assert "theorem bad : True" in user["failed_generated_declaration"]
    assert "unknown identifier 'missingFact'" in user["generated_only_lean_output"]
    assert "__repoprover_source_statement_check" not in prompt_text
    assert "theorem target" not in prompt_text


def test_source_statement_context_does_not_duplicate_notation_support(tmp_path: Path) -> None:
    project_root, record = _write_fixture_project(tmp_path)
    row = copy.deepcopy(record.row)
    row["minimal_context"]["lean_predecessors"] = [
        {"path": "Demo.lean", "declaration": "Demo.submatrixOfFinset", "line_range": [9, 13]},
    ]

    messages = build_messages(project_root, SelectedRecord(row))
    user = json.loads(messages[1]["content"])
    prefix = user["context"]["lean_prefix_context"]

    assert prefix.count("noncomputable def submatrixOfFinset") == 1
    assert "Do not redeclare definitions" in "\n".join(user["instructions"])
    assert "apply it to the needed variables" in "\n".join(user["instructions"])


def test_generated_application_candidates_try_explicit_then_all_binders() -> None:
    head = """theorem __repoprover_source_statement_check {n : ℕ} (d : Fin n → R) (P : Finset (Fin n)) :
    ((Matrix.diagonal d).submatrix (P.orderEmbOfFin rfl) (P.orderEmbOfFin rfl)).det =
    ∏ i ∈ P, d i"""

    assert generated_application_candidates("generated", head) == ["generated d P", "generated n d P", "generated"]


def test_generated_application_candidates_ignore_doc_comment_binders() -> None:
    head = """/-- Source says this holds for each `(k : ℕ)`. -/
theorem __repoprover_source_statement_check (k : ℕ) :
    (PowerSeries.X : PowerSeries ℚ) ^ k = PowerSeries.X ^ k"""

    assert generated_application_candidates("generated", head) == ["generated k", "generated"]


def test_generated_application_candidates_ignore_parenthesized_terms_in_statement() -> None:
    head = """theorem __repoprover_source_statement_check {lam mu : Fin N → ℕ} (T : Tableau lam mu) :
    (monomialTableau T : MvPolynomial (Fin N) R) = xPow (contentTableau T)"""

    assert generated_application_candidates("generated", head) == ["generated T", "generated lam mu T", "generated"]


def test_copy_local_import_closure_copies_recursive_local_imports(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    output_root = tmp_path / "out"
    dep = project_root / "AlgebraicCombinatorics" / "Dep.lean"
    mid = project_root / "AlgebraicCombinatorics" / "Mid.lean"
    dep.parent.mkdir(parents=True)
    dep.write_text("import Mathlib\n\ndef dep : True := True.intro\n", encoding="utf-8")
    mid.write_text("import AlgebraicCombinatorics.Dep\n\ndef mid : True := dep\n", encoding="utf-8")

    assert local_import_path("AlgebraicCombinatorics.Mid") == Path("AlgebraicCombinatorics/Mid.lean")
    assert import_modules_from_lean(mid) == ["AlgebraicCombinatorics.Dep"]

    copy_local_import_closure(
        project_root,
        output_root,
        ["Mathlib", "AlgebraicCombinatorics.Mid"],
        skip_paths=set(),
    )

    assert (output_root / "AlgebraicCombinatorics" / "Mid.lean").exists()
    assert (output_root / "AlgebraicCombinatorics" / "Dep.lean").exists()


def test_materialize_candidate_project_can_include_record_imports_without_copying_target(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    target = project_root / "AlgebraicCombinatorics" / "Target.lean"
    dep = project_root / "AlgebraicCombinatorics" / "Dep.lean"
    target.parent.mkdir(parents=True)
    (project_root / "lean-toolchain").write_text("leanprover/lean4:v4.28.0\n", encoding="utf-8")
    (project_root / "lake-manifest.json").write_text('{"version":"1.1.0","packages":[],"name":"demo"}\n', encoding="utf-8")
    (project_root / "lakefile.lean").write_text(
        "import Lake\nopen Lake DSL\npackage «demo» where\nlean_lib «AlgebraicCombinatorics» where\n  globs := #[.submodules `AlgebraicCombinatorics]\n",
        encoding="utf-8",
    )
    dep.write_text("import Mathlib\nnamespace AlgebraicCombinatorics\ndef dep : True := True.intro\nend AlgebraicCombinatorics\n", encoding="utf-8")
    target.write_text(
        "import Mathlib\nimport AlgebraicCombinatorics.Dep\nnamespace AlgebraicCombinatorics\ntheorem target : True := dep\nend AlgebraicCombinatorics\n",
        encoding="utf-8",
    )
    record = SelectedRecord(
        {
            "id": "AlgebraicCombinatorics/Target.lean:AlgebraicCombinatorics.target",
            "output": {
                "lean_path": "AlgebraicCombinatorics/Target.lean",
                "declaration_names": ["AlgebraicCombinatorics.target"],
                "line_range": [4, 4],
                "chunk_kind": "theorem",
            },
            "minimal_context": {
                "imports": ["Mathlib", "AlgebraicCombinatorics.Dep"],
                "file_context": [
                    {
                        "path": "AlgebraicCombinatorics/Target.lean",
                        "kind": "namespace",
                        "name": "AlgebraicCombinatorics",
                        "line_range": [3, 3],
                    },
                ],
                "lean_predecessors": [],
                "source_spans": [{"path": "source.tex", "line_range": [1, 1]}],
            },
        }
    )
    (project_root / "source.tex").write_text("true\n", encoding="utf-8")

    target_path = materialize_candidate_project(
        project_root=project_root,
        output_root=tmp_path / "out",
        record=record,
        lean_declaration="theorem generated : True := dep",
        generated_name="generated",
        lake_cache_from=None,
        include_record_imports=True,
    )

    text = target_path.read_text(encoding="utf-8")
    assert "import AlgebraicCombinatorics.Dep" in text
    assert "theorem target : True := dep" not in text
    assert (tmp_path / "out" / "AlgebraicCombinatorics" / "Dep.lean").exists()


def test_materialize_candidate_project_can_omit_grader_for_repair_prompts(tmp_path: Path) -> None:
    project_root, record = _write_fixture_project(tmp_path)

    target_path = materialize_candidate_project(
        project_root=project_root,
        output_root=tmp_path / "out",
        record=record,
        lean_declaration="theorem generated : True := by\n  trivial",
        generated_name="generated",
        lake_cache_from=None,
        include_grader=False,
    )

    text = target_path.read_text(encoding="utf-8")
    assert "theorem generated : True := by" in text
    assert "__repoprover_source_statement_check" not in text
    assert "theorem target" not in text


def test_materialize_candidate_project_can_reuse_existing_output_root(tmp_path: Path) -> None:
    project_root, record = _write_fixture_project(tmp_path)
    output_root = tmp_path / "out"
    output_root.mkdir()
    sentinel = output_root / "sentinel.txt"
    sentinel.write_text("keep me\n", encoding="utf-8")

    materialize_candidate_project(
        project_root=project_root,
        output_root=output_root,
        record=record,
        lean_declaration="theorem generated : True := by\n  trivial",
        generated_name="generated",
        lake_cache_from=None,
        include_grader=False,
        clean_output=False,
    )

    assert sentinel.exists()
    assert (output_root / "Demo.lean").exists()


def test_classify_lean_failure_separates_missing_mathlib_cache() -> None:
    output = "AlgebraicCombinatorics/CauchyBinet.lean:1:0: error: unknown module prefix 'Mathlib'\nNo directory 'Mathlib' or file 'Mathlib.olean'"

    assert classify_lean_failure(output) == "lean_environment_missing_mathlib_cache"


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
        "repair_attempts": 0,
        "repair_max_tokens": 128,
        "repair_reasoning_effort": None,
        "preflight_only": False,
        "reuse_project": False,
        "lake_cache_from": None,
        "include_record_imports": False,
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
    generated_path = tmp_path / "out/record-001/generated-lean-declaration.lean"
    assert generated_path.read_text(encoding="utf-8") == "theorem generated : True := by\n  trivial\n"
    parsed_json_path = tmp_path / "out/record-001/model-output.json"
    assert json.loads(parsed_json_path.read_text(encoding="utf-8"))["declaration_name"] == "generated"


def test_source_statement_live_eval_repairs_generated_only_compile_failure(
    tmp_path: Path, monkeypatch
) -> None:
    project_root, record = _write_fixture_project(tmp_path)
    records_path = tmp_path / "records.jsonl"
    _write_records(records_path, record.row, 1)
    calls: list[dict] = []
    responses = [
        {
            "lean_declaration": "theorem bad : True := by\n  exact missingFact",
            "declaration_name": "bad",
            "used_context": [],
            "notes": [],
        },
        {
            "lean_declaration": "theorem repaired : True := by\n  trivial",
            "declaration_name": "repaired",
            "used_context": ["compiler error"],
            "notes": [],
        },
    ]

    def fake_call_openrouter(payload: dict, base_url: str, timeout: float) -> dict:
        calls.append(payload)
        return _fake_response(json.dumps(responses[len(calls) - 1]), cost=0.0002)

    def fake_run_lean(project_root: Path, target_path: Path, timeout: int) -> dict:
        text = target_path.read_text(encoding="utf-8")
        if "missingFact" in text:
            return {"exit_code": 1, "output": "unknown identifier 'missingFact'"}
        return {"exit_code": 0, "output": ""}

    monkeypatch.setattr("scripts.run_source_statement_live_eval.call_openrouter", fake_call_openrouter)
    monkeypatch.setattr("scripts.run_source_statement_live_eval.run_lean", fake_run_lean)

    summary = run(_run_args(project_root, records_path, tmp_path / "out", limit=1, repair_attempts=1))
    row = summary["results"][0]

    assert len(calls) == 2
    assert summary["paid_calls_made"] == 2
    assert summary["actual_cost_usd"] == 0.0004
    assert summary["successes"] == 1
    assert row["repair_attempts_used"] == 1
    assert row["final_declaration_source"] == "repair-attempt-001"
    assert (tmp_path / "out/record-001/generated-only-lean.json").exists()
    assert (tmp_path / "out/record-001/repair-attempt-001-openrouter-payload.json").exists()
    assert (tmp_path / "out/record-001/repair-attempt-001-lean-declaration.lean").read_text(encoding="utf-8") == (
        "theorem repaired : True := by\n  trivial\n"
    )


def test_source_statement_live_eval_does_not_repair_grader_failures(tmp_path: Path, monkeypatch) -> None:
    project_root, record = _write_fixture_project(tmp_path)
    records_path = tmp_path / "records.jsonl"
    _write_records(records_path, record.row, 1)
    calls = 0

    def fake_call_openrouter(payload: dict, base_url: str, timeout: float) -> dict:
        nonlocal calls
        calls += 1
        body = json.dumps(
            {
                "lean_declaration": "theorem generated : True := by\n  trivial",
                "declaration_name": "generated",
                "used_context": [],
                "notes": [],
            }
        )
        return _fake_response(body)

    def fake_run_lean(project_root: Path, target_path: Path, timeout: int) -> dict:
        text = target_path.read_text(encoding="utf-8")
        if "__repoprover_source_statement_check" in text:
            return {"exit_code": 1, "output": "error: unsolved goals\n__repoprover_source_statement_check"}
        return {"exit_code": 0, "output": ""}

    monkeypatch.setattr("scripts.run_source_statement_live_eval.call_openrouter", fake_call_openrouter)
    monkeypatch.setattr("scripts.run_source_statement_live_eval.run_lean", fake_run_lean)

    summary = run(_run_args(project_root, records_path, tmp_path / "out", limit=1, repair_attempts=1))
    row = summary["results"][0]

    assert calls == 1
    assert summary["paid_calls_made"] == 1
    assert summary["successes"] == 0
    assert row["repair_attempts_used"] == 0
    assert row["repair_results"] == []
    assert summary["failure_classes"] == {"grader_gold_statement_not_proved": 1}


def test_source_statement_live_eval_preflight_makes_no_openrouter_call(tmp_path: Path, monkeypatch) -> None:
    project_root, record = _write_fixture_project(tmp_path)
    records_path = tmp_path / "records.jsonl"
    _write_records(records_path, record.row, 2)

    def fail_call_openrouter(payload: dict, base_url: str, timeout: float) -> dict:
        raise AssertionError("preflight must not call OpenRouter")

    monkeypatch.setattr("scripts.run_source_statement_live_eval.call_openrouter", fail_call_openrouter)
    monkeypatch.setattr(
        "scripts.run_source_statement_live_eval.run_lean",
        lambda project_root, target_path, timeout: {"exit_code": 0, "output": ""},
    )

    summary = run(
        _run_args(
            project_root,
            records_path,
            tmp_path / "out",
            limit=2,
            preflight_only=True,
            reuse_project=True,
            concurrency=1,
        )
    )

    assert summary["records_attempted"] == 0
    assert summary["paid_calls_made"] == 0
    assert summary["successes"] == 0
    assert summary["preflight_successes"] == 2
    assert summary["preflight_success_rate"] == 1.0
    assert [row["status"] for row in summary["results"]] == ["preflight_only", "preflight_only"]
    assert all(row["success"] for row in summary["results"])
    assert (tmp_path / "out/shared-project/Demo.lean").exists()


def test_source_statement_live_eval_reuse_project_requires_serial_execution(tmp_path: Path) -> None:
    project_root, record = _write_fixture_project(tmp_path)
    records_path = tmp_path / "records.jsonl"
    _write_records(records_path, record.row, 1)

    try:
        run(_run_args(project_root, records_path, tmp_path / "out", reuse_project=True, concurrency=2))
    except ValueError as exc:
        assert "--reuse-project requires --concurrency 1" in str(exc)
    else:
        raise AssertionError("expected --reuse-project to reject concurrent execution")


def test_source_statement_live_eval_persists_raw_assistant_content_before_json_parse(
    tmp_path: Path, monkeypatch
) -> None:
    project_root, record = _write_fixture_project(tmp_path)
    records_path = tmp_path / "records.jsonl"
    _write_records(records_path, record.row, 1)
    raw_content = "not json, but this is the model text we paid for"

    monkeypatch.setattr(
        "scripts.run_source_statement_live_eval.call_openrouter",
        lambda payload, base_url, timeout: _fake_response(raw_content),
    )

    summary = run(_run_args(project_root, records_path, tmp_path / "out", limit=1))

    assert summary["failure_classes"] == {"invalid_model_json": 1}
    raw_path = tmp_path / "out/record-001/model-assistant-content.txt"
    assert raw_path.read_text(encoding="utf-8") == raw_content


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
