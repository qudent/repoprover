"""Tests for archived source-statement generation artifact consumers."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.repair_source_statement_generation import run as run_repair_queue
from scripts.compare_source_statement_context_modes import compare_runs
from scripts.diagnose_source_statement_shape import diagnose_shape, run as run_shape_diagnostic
from scripts.run_source_statement_live_eval import build_repair_messages
from scripts.verify_source_statement_generation import load_tasks


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def _fake_response(body: str, *, cost: float = 0.001) -> dict:
    return {
        "model": "deepseek/deepseek-v4-pro",
        "choices": [{"message": {"content": body}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30, "cost": cost},
    }


def _write_archived_run(tmp_path: Path) -> Path:
    run_output = tmp_path / "run"
    _write_jsonl(
        run_output / "eval/selected-records.jsonl",
        [
            {"id": "Demo.lean:Demo.bad"},
            {"id": "Demo.lean:Demo.good"},
        ],
    )
    _write_json(
        run_output / "eval/verification-results.json",
        {
            "results": [
                {
                    "index": 1,
                    "record_id": "Demo.lean:Demo.bad",
                    "failure_class": "generated_lean_does_not_compile",
                },
                {
                    "index": 2,
                    "record_id": "Demo.lean:Demo.good",
                    "failure_class": "grader_gold_statement_not_proved",
                },
            ]
        },
    )
    original_user = {"context": {"lean_prefix_context": "namespace Demo"}, "instructions": []}
    _write_json(
        run_output / "record-001/openrouter-payload.json",
        {"messages": [{"role": "system", "content": "system"}, {"role": "user", "content": json.dumps(original_user)}]},
    )
    _write_json(
        run_output / "record-001/model-output.json",
        {
            "lean_declaration": "theorem bad : True := by\n  exact missingFact",
            "declaration_name": "bad",
        },
    )
    _write_json(
        run_output / "record-001/verification-generated-only-lean.json",
        {"exit_code": 1, "output": "unknown identifier 'missingFact'"},
    )
    return run_output


def _repair_args(run_output: Path, **overrides) -> argparse.Namespace:
    values = {
        "run_output": run_output,
        "verification_results": "verification-results.json",
        "failed_model_output_name": "model-output.json",
        "generated_only_lean_name": "verification-generated-only-lean.json",
        "attempt": 1,
        "model": "deepseek/deepseek-v4-pro",
        "base_url": "https://openrouter.ai/api/v1",
        "max_tokens": 128,
        "temperature": 0.0,
        "reasoning_effort": "high",
        "openrouter_timeout": 30.0,
        "max_actual_cost_usd": 0.25,
        "concurrency": 2,
        "budget_only": False,
        "include_non_compile_failures": False,
        "shape_diagnostic_results": None,
        "include_shape_warnings": False,
        "shape_warnings_only": False,
        "indices": None,
    }
    values.update(overrides)
    return argparse.Namespace(**values)


def test_repair_queue_targets_compile_failures_and_writes_payload(tmp_path: Path) -> None:
    run_output = _write_archived_run(tmp_path)

    summary = run_repair_queue(_repair_args(run_output, budget_only=True))

    assert summary["records_completed"] == 1
    assert summary["paid_calls_made"] == 0
    payload = json.loads((run_output / "record-001/repair-attempt-001-openrouter-payload.json").read_text(encoding="utf-8"))
    user = json.loads(payload["messages"][1]["content"])
    assert "theorem bad : True" in user["failed_generated_declaration"]
    assert "unknown identifier 'missingFact'" in user["generated_only_lean_output"]
    assert not (run_output / "record-002/repair-attempt-001-openrouter-payload.json").exists()


def test_repair_queue_can_target_shape_warning_rows(tmp_path: Path) -> None:
    run_output = _write_archived_run(tmp_path)
    _write_json(
        run_output / "record-002/model-output.json",
        {
            "lean_declaration": "theorem generated : True := by\n  trivial",
            "declaration_name": "generated",
        },
    )
    _write_json(run_output / "record-002/verification-generated-only-lean.json", {"exit_code": 0, "output": ""})
    _write_json(
        run_output / "record-002/openrouter-payload.json",
        {"messages": [{"role": "system", "content": "system"}, {"role": "user", "content": json.dumps({"context": {}})}]},
    )
    _write_json(
        run_output / "eval/shape-diagnostic-results.json",
        {
            "results": [
                {"index": 1, "warnings": []},
                {
                    "index": 2,
                    "warnings": [
                        {
                            "code": "pointwise_conclusion_instead_of_sequence_equality",
                            "message": "Visible context asks for sequence equality.",
                        }
                    ],
                },
            ]
        },
    )

    summary = run_repair_queue(
        _repair_args(
            run_output,
            budget_only=True,
            include_shape_warnings=True,
            shape_diagnostic_results="shape-diagnostic-results.json",
        )
    )

    assert summary["records_completed"] == 2
    assert summary["include_shape_warnings"] is True
    payload = json.loads((run_output / "record-002/repair-attempt-001-openrouter-payload.json").read_text(encoding="utf-8"))
    user = json.loads(payload["messages"][1]["content"])
    assert user["shape_diagnostic_warnings"][0]["code"] == "pointwise_conclusion_instead_of_sequence_equality"


def test_repair_queue_can_limit_to_indices(tmp_path: Path) -> None:
    run_output = _write_archived_run(tmp_path)
    _write_json(
        run_output / "record-002/model-output.json",
        {
            "lean_declaration": "theorem generated : True := by\n  trivial",
            "declaration_name": "generated",
        },
    )
    _write_json(run_output / "record-002/verification-generated-only-lean.json", {"exit_code": 0, "output": ""})
    _write_json(
        run_output / "record-002/openrouter-payload.json",
        {"messages": [{"role": "system", "content": "system"}, {"role": "user", "content": json.dumps({"context": {}})}]},
    )

    summary = run_repair_queue(_repair_args(run_output, budget_only=True, include_non_compile_failures=True, indices=[2]))

    assert summary["records_completed"] == 1
    assert summary["results"][0]["index"] == 2
    assert not (run_output / "record-001/repair-attempt-001-openrouter-payload.json").exists()
    assert (run_output / "record-002/repair-attempt-001-openrouter-payload.json").exists()


def test_repair_queue_writes_repair_model_artifacts(tmp_path: Path, monkeypatch) -> None:
    run_output = _write_archived_run(tmp_path)

    def fake_call_openrouter(payload: dict, base_url: str, timeout: float) -> dict:
        body = json.dumps(
            {
                "lean_declaration": "theorem repaired : True := by\n  trivial",
                "declaration_name": "repaired",
                "used_context": ["compiler error"],
                "notes": [],
            }
        )
        return _fake_response(body, cost=0.0002)

    monkeypatch.setattr("scripts.repair_source_statement_generation.call_openrouter", fake_call_openrouter)

    summary = run_repair_queue(_repair_args(run_output))

    assert summary["paid_calls_made"] == 1
    assert summary["actual_cost_usd"] == 0.0002
    assert summary["repair_generation_successes"] == 1
    assert (run_output / "record-001/repair-attempt-001-model-output.json").exists()
    assert (run_output / "record-001/repair-attempt-001-lean-declaration.lean").read_text(encoding="utf-8") == (
        "theorem repaired : True := by\n  trivial\n"
    )


def test_repair_queue_uses_estimated_reservations_for_cost_cap(tmp_path: Path, monkeypatch) -> None:
    run_output = _write_archived_run(tmp_path)
    called = False

    def fake_call_openrouter(payload: dict, base_url: str, timeout: float) -> dict:
        nonlocal called
        called = True
        return _fake_response("{}")

    monkeypatch.setattr("scripts.repair_source_statement_generation.call_openrouter", fake_call_openrouter)

    summary = run_repair_queue(_repair_args(run_output, max_actual_cost_usd=0.000001, concurrency=2))

    assert called is False
    assert summary["paid_calls_made"] == 0
    assert summary["failure_classes"] == {"skipped_cost_cap": 1}
    assert summary["results"][0]["failure_class"] == "skipped_cost_cap"


def test_repair_prompt_adds_negative_binomial_helper_guidance() -> None:
    original_user = {"context": {"lean_prefix_context": "theorem fps_onePlusX_pow_neg' {F : Type*} (n : ℕ) : True := by trivial"}}
    messages = build_repair_messages(
        original_messages=[{"role": "system", "content": ""}, {"role": "user", "content": json.dumps(original_user)}],
        failed_declaration="theorem generated (F : Type*) (n : ℕ) : True := by\n  exact fps_onePlusX_pow_neg' F n",
        generated_only_lean_result={"exit_code": 1, "output": "Application type mismatch: fps_onePlusX_pow_neg' F"},
    )
    user = json.loads(messages[1]["content"])
    guidance_text = json.dumps(user["repair_domain_guidance"], ensure_ascii=False)

    assert "fps_onePlusX_pow_neg' (F := F) n" in guidance_text
    assert "fps_onePlusX_pow_neg' F n" in guidance_text
    assert "integer powers" in guidance_text


def test_repair_prompt_adds_finite_finsum_support_guidance() -> None:
    original_user = {"context": {"lean_prefix_context": "theorem fps_subs_wd_firstCoeffs : True := by trivial"}}
    messages = build_repair_messages(
        original_messages=[{"role": "system", "content": ""}, {"role": "user", "content": json.dumps(original_user)}],
        failed_declaration=(
            "theorem generated : True := by\n"
            "  apply finsum_eq_sum_of_support_subset\n"
            "  intro d hd\n"
            "  exact hd"
        ),
        generated_only_lean_result={
            "exit_code": 1,
            "output": "hd has type d ∈ Function.support fun i => t i but is expected to have type n < d",
        },
    )
    user = json.loads(messages[1]["content"])
    guidance_text = json.dumps(user["repair_domain_guidance"], ensure_ascii=False)

    assert "support-subset goal" in guidance_text
    assert "Function.mem_support" in guidance_text
    assert "mul_zero" in guidance_text
    assert "Do not treat `hd`" in guidance_text


def test_verifier_can_load_repair_model_outputs(tmp_path: Path) -> None:
    run_output = _write_archived_run(tmp_path)
    _write_json(
        run_output / "record-001/repair-attempt-001-model-output.json",
        {
            "lean_declaration": "theorem repaired : True := by\n  trivial",
            "declaration_name": "repaired",
        },
    )

    tasks = load_tasks(run_output, model_output_name="repair-attempt-001-model-output.json")

    assert tasks[0]["model_output_path"].endswith("repair-attempt-001-model-output.json")
    assert tasks[1]["failure_class"] == "missing_model_output"


def test_verifier_load_tasks_can_filter_indices(tmp_path: Path) -> None:
    run_output = _write_archived_run(tmp_path)

    tasks = load_tasks(run_output, indices={2})

    assert [task["index"] for task in tasks] == [2]


def test_compare_context_modes_flags_lost_domains_and_hidden_names(tmp_path: Path) -> None:
    target_run = tmp_path / "target"
    source_run = tmp_path / "source"
    _write_jsonl(
        source_run / "eval/selected-records.jsonl",
        [
            {
                "id": "Demo.lean:Demo.secretName",
                "output": {"declaration_names": ["Demo.secretName"]},
            }
        ],
    )
    _write_json(
        source_run / "eval/source-statement-live-results.json",
        {"results": [{"index": 1, "budget_estimate": {"estimated_max_cost_usd": 0.01}}]},
    )
    _write_json(target_run / "eval/source-statement-live-results.json", {"results": []})
    target_user = {
        "context": {
            "context_mode": "target-comment",
            "source_statement_or_chunk": [{"snippet": "Let f be summable."}],
            "target_source_focus": {"target_declaration_source_comment": {"text": "Alternative coefficient formula."}},
            "domain_statement_shape_guidance": [{"domain": "finite coefficient"}],
        }
    }
    source_user = {
        "context": {
            "context_mode": "source-only",
            "source_statement_or_chunk": [{"snippet": "Let f be summable."}],
            "target_source_focus": {"target_declaration_source_comment": None},
            "domain_statement_shape_guidance": [],
        }
    }
    _write_json(
        target_run / "record-001/openrouter-payload.json",
        {"messages": [{"role": "user", "content": json.dumps(target_user)}]},
    )
    _write_json(
        source_run / "record-001/openrouter-payload.json",
        {"messages": [{"role": "user", "content": json.dumps(source_user)}]},
    )

    summary = compare_runs(target_run, source_run)

    assert summary["records_with_lost_domains"] == 1
    assert summary["records_with_target_comment_terms_absent_from_source"] == 1
    assert summary["records_with_hidden_target_names_in_source_payload"] == 0
    assert summary["results"][0]["lost_domains"] == ["finite coefficient"]
    assert "alternative" in summary["results"][0]["target_comment_terms_absent_from_source"]


def test_shape_diagnostic_flags_pointwise_sequence_equality() -> None:
    warnings = diagnose_shape(
        {
            "context": {
                "domain_statement_shape_guidance": [
                    {
                        "preferred_statement_family": [
                            "For equality of embedded bivariate series, prove sequence equality by `funext k`."
                        ]
                    }
                ],
                "local_lean_style": {"examples": ["theorem coeff_embedUnivInBiv : True := by trivial"]},
            }
        },
        "lemma generated (h : embedUnivInBiv f = embedUnivInBiv g) : ∀ k, f k = g k := by\n  intro k\n  sorry",
    )

    assert [warning["code"] for warning in warnings] == ["pointwise_conclusion_instead_of_sequence_equality"]


def test_shape_diagnostic_flags_wrong_x_power_shape() -> None:
    warnings = diagnose_shape(
        {
            "context": {
                "target_source_focus": {
                    "target_declaration_source_comment": {
                        "text": "f * X^k shifts f by k positions (generalization of Lemma lem.fps.xa)"
                    }
                },
                "domain_statement_shape_guidance": [
                    {
                        "preferred_statement_family": [
                            "For shifted-coefficient targets, prefer the displayed coefficient theorem shape."
                        ]
                    }
                ],
            }
        },
        "theorem generated (a : R⟦X⟧) : X * a = PowerSeries.mk (fun n => coeff n a) := by\n  ext n\n  simp",
    )

    assert [warning["code"] for warning in warnings] == ["wrong_x_power_multiplication_side_or_shape"]


def test_shape_diagnostic_does_not_use_domain_guidance_as_x_power_source() -> None:
    warnings = diagnose_shape(
        {
            "context": {
                "source_statement_or_chunk": [
                    {"snippet": "Lemma lem.fps.xa: x a = (0, a_0, a_1, ...)."}
                ],
                "domain_statement_shape_guidance": [
                    {
                        "preferred_statement_family": [
                            "For shifted-coefficient targets, prefer the `f * X ^ k` theorem shape."
                        ]
                    }
                ],
            }
        },
        "theorem X_mul_eq_shift (f : R⟦X⟧) : X * f = PowerSeries.mk (fun n => if n = 0 then 0 else coeff (n-1) f) := by\n  ext n\n  simp",
    )

    assert [warning["code"] for warning in warnings] == []


def test_shape_diagnostic_flags_fin_object_inequalities() -> None:
    warnings = diagnose_shape(
        {
            "context": {
                "target_source_focus": {
                    "target_declaration_source_comment": {
                        "text": "Simple transposition `s_i` fixes any `k ≠ i, i+1`."
                    }
                },
                "domain_statement_shape_guidance": [
                    {"preferred_statement_family": ["For the fixed-point theorem, prefer assumptions on values."]}
                ],
            }
        },
        "theorem generated (i : Fin (n - 1)) (k : Fin n) (h1 : k ≠ ⟨i.val, by omega⟩) : simpleTransposition i k = k := by\n  simp",
    )

    assert [warning["code"] for warning in warnings] == ["fin_object_inequality_instead_of_value_inequality"]


def test_shape_diagnostic_flags_simple_transposition_equality_instead_of_isswap() -> None:
    warnings = diagnose_shape(
        {
            "context": {
                "source_statement_or_chunk": [
                    {
                        "snippet": "A simple transposition is a transposition that swaps two consecutive integers."
                    }
                ],
                "domain_statement_shape_guidance": [{"domain": "simple transposition statement shape"}],
            }
        },
        "theorem simpleTransposition_eq_transposition (i : Fin (n - 1)) : simpleTransposition i = transposition i := by\n  rfl",
    )

    assert [warning["code"] for warning in warnings] == ["simple_transposition_equality_instead_of_isswap"]


def test_repair_guidance_handles_missing_swap_isswap_helper() -> None:
    messages = build_repair_messages(
        original_messages=[
            {"role": "system", "content": ""},
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "context": {
                            "domain_statement_shape_guidance": [
                                {"domain": "simple transposition statement shape"}
                            ]
                        }
                    }
                ),
            },
        ],
        failed_declaration=(
            "theorem simpleTransposition_isSwap {n : ℕ} (i : Fin (n - 1)) : "
            "(simpleTransposition i).IsSwap := by\n"
            "  unfold simpleTransposition; exact Equiv.swap_isSwap _ _"
        ),
        generated_only_lean_result={
            "exit_code": 1,
            "output": "error(lean.unknownIdentifier): Unknown constant `Equiv.swap_isSwap`",
        },
    )
    user = json.loads(messages[1]["content"])
    guidance_text = json.dumps(user["repair_domain_guidance"], ensure_ascii=False)

    assert "Do not use `Equiv.swap_isSwap`" in guidance_text
    assert "constructor-style proof shape" in guidance_text
    assert "(simpleTransposition i).IsSwap" in guidance_text
    assert "prefer direct witness introduction" in guidance_text
    assert "Avoid `let b : Fin n" in guidance_text


def test_shape_diagnostic_flags_pointwise_permutation_power() -> None:
    warnings = diagnose_shape(
        {
            "context": {
                "target_source_focus": {
                    "target_declaration_source_comment": {
                        "text": "For `i ≥ 0`, `α^i = α ∘ α ∘ ⋯ ∘ α` (i times)."
                    }
                },
                "domain_statement_shape_guidance": [
                    {
                        "preferred_statement_family": [
                            "When the source focus is the group-power law for `α^(n+1)`, prefer the theorem statement `α ^ (n + 1) = α ^ n * α` over a pointwise statement about iterated functions."
                        ],
                        "avoid_statement_family": [
                            "Do not formalize the power law as `Function.iterate`/`^[n]` unless the source focus explicitly asks for pointwise iteration."
                        ],
                    }
                ],
            }
        },
        "theorem generated {X : Type*} (α : Equiv.Perm X) (n : ℕ) (x : X) : (α ^ (n + 1)) x = (α^[n + 1]) x := by\n  sorry",
    )

    assert [warning["code"] for warning in warnings] == ["pointwise_iteration_instead_of_group_power_statement"]


def test_shape_diagnostic_flags_weak_hprod_contract() -> None:
    warnings = diagnose_shape(
        {
            "context": {
                "target_source_focus": {
                    "target_declaration_source_comment": {
                        "text": "The hypothesis `hprod` says that `prod_f` is the infinite product: for any approximator `M`, the coefficient of `prod_f` equals the coefficient of the finite product over `M`."
                    }
                }
            }
        },
        "theorem generated (prod_f : PowerSeries K) (hprod : ∀ n, ∃ M : Finset I, coeff n prod_f = coeff n (∏ i ∈ M, f i)) : True := by\n  trivial",
    )

    assert [warning["code"] for warning in warnings] == ["weak_exists_hprod_instead_of_any_approximator_contract"]


def test_shape_diagnostic_flags_infprod_conclusion_bundling() -> None:
    warnings = diagnose_shape(
        {
            "context": {
                "target_source_focus": {
                    "target_declaration_source_comment": {
                        "text": "The hypothesis `hprod` says that `prod_f` is the infinite product: for any approximator `M`, the coefficient of `prod_f` equals the coefficient of the finite product over `M`."
                    }
                }
            }
        },
        "theorem generated (prod_f : PowerSeries K) (hprod : True) : ∀ n, ∃ M : Finset I, (∀ J : Finset I, M ⊆ J → coeff n (∏ i ∈ J, f i) = coeff n (∏ i ∈ M, f i)) ∧ coeff n (prod_f.subst g) = coeff n (∏ i ∈ M, (f i).subst g) := by\n  sorry",
    )

    assert [warning["code"] for warning in warnings] == ["infprod_conclusion_bundles_approximator_proof"]


def test_shape_diagnostic_allows_finite_finsum_comp_helper() -> None:
    warnings = diagnose_shape(
        {
            "context": {
                "domain_statement_shape_guidance": [
                    {
                        "preferred_statement_family": [
                            "For finite coefficient formulas for substitution, derive the infinite coefficient formula from `fps_comp_coeff`, then restrict the finite sum with `finsum_eq_sum_of_support_subset`.",
                        ],
                        "avoid_statement_family": [
                            "Do not use the finite-composition helper with a separately inferred `constantCoeff X = 0` when a direct `HasSubst.X'` proof is available.",
                        ],
                    }
                ],
                "local_lean_style": {"examples": ["have ha : HasSubst (X : K⟦X⟧) := HasSubst.X'\nrw [coeff_subst' ha g n]"]},
            }
        },
        "theorem generated : True := by\n  rw [fps_comp_coeff f g hg n]\n  apply finsum_eq_sum_of_support_subset",
    )

    assert warnings == []


def test_shape_diagnostic_writes_run_artifacts(tmp_path: Path) -> None:
    run_output = tmp_path / "run"
    _write_jsonl(run_output / "eval/selected-records.jsonl", [{"id": "Demo.lean:Demo.generated"}])
    user_payload = {
        "context": {
            "target_source_focus": {
                "target_declaration_source_comment": {"text": "g ∘ X = g; use `PowerSeries.subst X g`."}
            }
        }
    }
    _write_json(
        run_output / "record-001/openrouter-payload.json",
        {"messages": [{"role": "user", "content": json.dumps(user_payload)}]},
    )
    _write_json(
        run_output / "record-001/model-output.json",
        {
            "lean_declaration": "theorem generated (g : K⟦X⟧) : PowerSeries.subst g X = g := by\n  simp",
            "declaration_name": "generated",
        },
    )

    summary = run_shape_diagnostic(
        argparse.Namespace(
            run_output=run_output,
            payload_name="openrouter-payload.json",
            model_output_name="model-output.json",
        )
    )

    assert summary["records_with_warnings"] == 1
    assert summary["warning_codes"] == {"substitution_argument_order_swapped": 1}
    assert (run_output / "eval/shape-diagnostic-results.md").exists()
    assert (run_output / "record-001/shape-diagnostic.json").exists()
