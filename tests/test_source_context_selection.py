"""Tests for source-only context-selection prompts and artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.apply_context_selection_to_records import apply_context_selection
from scripts.materialize_minimal_context_smoke import SelectedRecord
from scripts.run_source_context_selection import (
    BatchItem,
    build_context_selection_messages,
    hydrate_mathlib_context,
    run,
)


def _write_selector_fixture(tmp_path: Path) -> tuple[Path, SelectedRecord]:
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / ".lake/packages/mathlib/Mathlib/Data/Nat/Choose").mkdir(parents=True)
    (project_root / ".lake/packages/mathlib/Mathlib/Data/Nat/Choose/Basic.lean").write_text(
        "\n".join(
            [
                "namespace Nat",
                "",
                "/-- Symmetry of natural-number binomial coefficients. -/",
                "theorem choose_symm {n k : Nat} (h : k ≤ n) : n.choose k = n.choose (n - k) := by",
                "  sorry",
                "",
                "end Nat",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (project_root / "Demo.lean").write_text(
        "\n".join(
            [
                "import Mathlib",
                "",
                "namespace Demo",
                "",
                "variable (n k : Nat)",
                "",
                "/-- Visible local helper before the target. -/",
                "theorem visible_helper : True := by",
                "  trivial",
                "",
                "/-- Part (a) of Lemma \\ref{demo.binom} in the source. -/",
                "theorem prior_part : True := by",
                "  trivial",
                "",
                "/-- Target declaration comment must not be exposed.",
                "    Label: demo.binom.hidden -/",
                "theorem hiddenTarget (h : k ≤ n) : True := by",
                "  trivial",
                "",
                "end Demo",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (project_root / "Demo.tex").write_text(
        "\\begin{theorem}\\label{demo.binom} Binomial coefficients are symmetric.\\end{theorem}\n",
        encoding="utf-8",
    )
    row = {
        "id": "Demo.lean:Demo.hiddenTarget",
        "alignment": {
            "comment_labels": ["demo.binom", "demo.binom.hidden"],
            "paired_source_path": "Demo.tex",
            "source_method": "lean_comment_label",
        },
        "output": {
            "lean_path": "Demo.lean",
            "declaration_names": ["Demo.hiddenTarget"],
            "line_range": [15, 18],
            "chunk_kind": "theorem",
        },
        "minimal_context": {
            "source_spans": [{"path": "Demo.tex", "line_range": [1, 1], "labels": ["demo.binom"]}],
            "file_context": [
                {"path": "Demo.lean", "kind": "namespace", "line_range": [3, 3], "name": "Demo"},
                {"path": "Demo.lean", "kind": "variable", "line_range": [5, 5], "name": "variable (n k : Nat)"},
            ],
            "lean_predecessors": [],
            "imports": ["Mathlib"],
            "mathlib_context": ["Mathlib APIs referenced by imported modules; exact proof-level facts not statically certified."],
        },
    }
    return project_root, SelectedRecord(row)


def test_context_selection_prompt_excludes_target_name_and_placeholder_mathlib(tmp_path: Path) -> None:
    project_root, record = _write_selector_fixture(tmp_path)

    messages = build_context_selection_messages(
        project_root,
        [BatchItem(public_key="record-001", record=record)],
        max_context_tokens=4000,
        round_name="round1",
    )

    prompt_text = json.dumps(messages, ensure_ascii=False)
    assert "record-001" in prompt_text
    assert "prior_part" in prompt_text
    assert "source_progress_context" in prompt_text
    assert "candidate_project_context" in prompt_text
    assert "hiddenTarget" not in prompt_text
    assert "Target declaration comment must not be exposed" not in prompt_text
    assert "exact proof-level facts not statically certified" not in prompt_text


def test_hydrate_mathlib_context_resolves_selected_declaration(tmp_path: Path) -> None:
    project_root, _ = _write_selector_fixture(tmp_path)

    hydrated = hydrate_mathlib_context(
        {
            "records": [
                {
                    "record_key": "record-001",
                    "candidate_mathlib_context": [{"name": "Nat.choose_symm"}],
                    "mathlib_queries": [],
                }
            ]
        },
        mathlib_workspace=project_root,
        max_results_per_query=2,
    )

    matches = hydrated["records"][0]["resolved_mathlib_context"][0]["matches"]
    assert matches
    assert "theorem choose_symm" in matches[0]["snippet"]


def test_context_selection_budget_run_writes_payload(tmp_path: Path) -> None:
    project_root, record = _write_selector_fixture(tmp_path)
    records_path = tmp_path / "records.jsonl"
    records_path.write_text(json.dumps(record.row) + "\n", encoding="utf-8")
    output = tmp_path / "out"

    summary = run(
        argparse.Namespace(
            records=records_path,
            project_root=project_root,
            output=output,
            limit=1,
            sample_mode="corpus-spread",
            batch_size=1,
            concurrency=1,
            model="deepseek/deepseek-v4-pro",
            base_url="https://openrouter.ai/api/v1",
            max_tokens=256,
            temperature=0.0,
            reasoning_effort="low",
            round_name="round1",
            max_context_tokens_per_record=4000,
            openrouter_timeout=30.0,
            max_actual_cost_usd=0.01,
            budget_only=True,
            hydrate_mathlib=False,
            compare_gold=False,
            mathlib_workspace=None,
            max_mathlib_results_per_query=2,
            use_live_catalog_prices=False,
        )
    )

    assert summary["records_selected"] == 1
    assert summary["paid_calls_made"] == 0
    payload_path = output / "batch-001/context-selection-payload.json"
    assert payload_path.exists()
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    assert payload["response_format"] == {"type": "json_object"}
    assert (output / "eval/context-selection-results.md").exists()


def test_apply_context_selection_injects_hydrated_mathlib_without_gold(tmp_path: Path) -> None:
    _, record = _write_selector_fixture(tmp_path)
    run_dir = tmp_path / "selector"
    (run_dir / "eval").mkdir(parents=True)
    (run_dir / "eval/selected-records.jsonl").write_text(json.dumps(record.row) + "\n", encoding="utf-8")
    (run_dir / "batch-001").mkdir()
    (run_dir / "batch-001/context-selection-output.json").write_text(
        json.dumps(
            {
                "records": [
                    {
                        "record_key": "record-001",
                        "source_focus_summary": "Binomial symmetry.",
                        "formalization_sketch": ["Use Nat.choose_symm."],
                        "candidate_mathlib_context": [
                            {
                                "name": "Nat.choose_symm",
                                "expected_signature_or_shape": "n.choose k = n.choose (n-k)",
                                "why_needed": "main proof fact",
                                "confidence": 1.0,
                            }
                        ],
                        "candidate_project_context": [
                            {
                                "name": "Demo.previous_fact",
                                "expected_signature_or_shape": "previously formalized source fact",
                                "why_needed": "avoid reproving the imported result",
                                "confidence": 0.9,
                            }
                        ],
                        "proof_notes": ["Use the displayed hypothesis."],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    (run_dir / "batch-001/mathlib-hydrated-context.json").write_text(
        json.dumps(
            {
                "records": [
                    {
                        "record_key": "record-001",
                        "resolved_mathlib_context": [
                            {
                                "query": "Nat.choose_symm",
                                "matches": [
                                    {
                                        "file": "Mathlib/Data/Nat/Choose/Basic.lean",
                                        "line": 4,
                                        "snippet": "theorem choose_symm {n k : Nat} (h : k ≤ n) : n.choose k = n.choose (n - k) := by\n  sorry",
                                    }
                                ],
                            }
                        ],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    output = tmp_path / "enhanced.jsonl"

    summary = apply_context_selection(
        argparse.Namespace(
            context_selection_run=run_dir,
            records=None,
            output=output,
            report_output=None,
            selector_model="fake",
            max_hydrated_chars_per_record=2000,
            keep_missing=False,
        )
    )

    assert summary["records_output"] == 1
    enhanced = json.loads(output.read_text(encoding="utf-8"))
    context = "\n".join(enhanced["minimal_context"]["mathlib_context"])
    assert "Nat.choose_symm" in context
    assert "Demo.previous_fact" in context
    assert "theorem choose_symm" in context
    assert enhanced["minimal_context"]["context_selection"]["used_gold_comparison"] is False
