# Source Context-Selection Pilot - 2026-05-05

## Purpose

This pilot starts the LLM-based context-selection layer requested for the
source-to-Lean pipeline. The selector sees source-only prompt context and prefix
Lean context, then returns:

- a formalization sketch;
- local context that should be retained;
- Mathlib names/search queries and expected signatures;
- proof notes and uncertainties.

The selector prompt does not include the target Lean name, statement, or proof.
Gold comparison is written only after selector output exists.

## New Pipeline Pieces

- Selector runner: `scripts/run_source_context_selection.py`
- Context applier: `scripts/apply_context_selection_to_records.py`
- Tests: `tests/test_source_context_selection.py`

The selector runner writes per-batch payloads, responses, cost summaries,
assistant content, parsed JSON, hydrated Mathlib snippets, and post-hoc gold
comparison artifacts. It also records a target-name payload leak audit in each
run summary.

The applier consumes a successful selector run and writes an enhanced records
JSONL by adding selector output and hydrated Mathlib snippets to
`minimal_context.mathlib_context`. It does not read `gold-comparison.json`.

## Dataset Used

The main budget audit used 8 corpus-spread theorem records from
`docs/minimal-context-gold-candidates.jsonl`:

1. `CauchyBinet.det_diagonal_submatrix_eq`
2. `FPS.module_add_zero`
3. `PowerSeries.tprod_fubini_full`
4. `FPS.binom_symm`
5. `Nat.Partition.parts_eq_zero_of_partition_zero`
6. `Equiv.Perm.sign_coe_eq_neg_one_pow_invCount`
7. `SymmetricPolynomials.Monomial.degree_ofFinset`
8. `alternant_swap`

Paid selector probes used smaller subsets from the same corpus-spread ordering.

## Model Probes

Live OpenRouter catalog IDs/prices were checked before use.

| Run | Records | Model | Reasoning | Result | Cost |
|---|---:|---|---|---|---:|
| `round1-kimi-k2.6-paid` | 4 | `moonshotai/kimi-k2.6` | `low` | no content, `finish_reason=length`, mostly reasoning tokens | `$0.0615948` |
| `round1-kimi-k2.6-noreason1-paid` | 1 | `moonshotai/kimi-k2.6` | omitted | no content, `finish_reason=length`, still reasoning tokens | `$0.02593245` |
| `round1-deepseek-v4-flash-paid` | 4 | `deepseek/deepseek-v4-flash` | `low` | no content, `finish_reason=length`, mostly reasoning tokens | `$0.00540708` |
| `round1-deepseek-v4-flash-noreason-paid` | 2 | `deepseek/deepseek-v4-flash` | omitted | valid JSON, hydrated Mathlib context, gold comparison | `$0.0025886` |
| `round1-deepseek-v4-flash-noreason4-paid` | 4 | `deepseek/deepseek-v4-flash` | omitted | partial text, truncated JSON | `$0.00540708` |
| `round1-gemini-2.5-flash-noreason-paid` | 2 | `google/gemini-2.5-flash` | omitted | partial text, truncated JSON | `$0.0147355` |

Total paid selector spend: `$0.11566551`.

## Best Selector Output

Best run:

`docs/source-statement-runs/2026-05-05-context-selection-round1-deepseek-v4-flash-noreason-paid/`

This used 2 records in one batch, produced valid JSON, and had
`payload_target_name_audit.leak_count = 0`.

For `det_diagonal_submatrix_eq`, the selector requested relevant Mathlib facts
such as `Matrix.det_diagonal`, `Matrix.diagonal_apply`, and product congruence
facts. Hydration resolved `Matrix.det_diagonal` exactly, and post-hoc gold
comparison found overlap on `det_diagonal`.

For `alternant_swap`, the selector requested `Equiv.Perm.sign_swap`,
`Equiv.Perm.sign_mul`, `Finset.sum_involution`, and
`Equiv.Perm.mul_swap_involutive`; hydration resolved these to real Mathlib
source snippets. The mathematical sketch was plausible, but it selected both
parts of the broad source lemma.

## Context-Selected Generation Probe

The successful selector output was applied to records here:

`docs/source-statement-runs/2026-05-05-context-selection-round1-deepseek-v4-flash-noreason-paid/eval/context-selected-records.jsonl`

Generation-only run:

`docs/source-statement-runs/2026-05-05-context-selected-generation-paid/`

Results:

- Record 1 provider call failed before a response:
  `openrouter_JSONDecodeError`.
- Record 2 generated `alternant_properties`, cost `$0.02031073`.
- Raw generation artifacts were committed before verification in commit
  `8c311dc`.
- Verification passed `0/2`: one `missing_model_output`, one
  `generated_lean_does_not_compile`.

Generated record 2 did show useful mathematical understanding:

- it used `Equiv.Perm.sign_swap`, `sign_mul`, `Finset.sum_involution`, and
  reindexing;
- it failed on Lean details (`noncomputable`, stuck `OfNat` metavariable);
- more importantly, it bundled both source parts as an `∧`, while the target was
  only the swap statement.

So the current failure is not just Mathlib type-signature recall. It is also a
source-focus failure: broad LaTeX theorem environments still make the selector
choose too much unless the pipeline identifies the exact part to formalize.

## Practical Takeaways

- Use no-reasoning mode for cheap selector models. Reasoning mode consumed the
  output budget and returned no usable JSON for Kimi K2.6 and DeepSeek V4 Flash.
- With the current verbose schema, batch size 2 is viable; batch size 4 often
  truncates.
- DeepSeek V4 Flash is currently the best cheap selector among the probes:
  it produced valid structured output and useful Mathlib queries for `$0.0026`.
- Kimi K2.6 is not usable with this prompt shape yet; even a single-record
  no-reasoning probe returned no content after hidden reasoning.
- Gemini 2.5 Flash returned text but not valid JSON at 4k output; it may need a
  tighter schema or larger output cap.
- The next improvement should shrink selector output and add a source-part
  disambiguation round before generation.

## Next Steps

1. Split selection into two compact rounds:
   source-part/formalization target selection first, Mathlib API selection
   second.
2. Reduce selector schema verbosity so 4-record batches can finish in JSON.
3. Feed only one selected source part into generation, especially for broad
   theorem environments with `(a)/(b)` parts.
4. Retry context-selected generation on a 4-record diverse slice only after the
   selector can avoid conjunction over-bundling on known broad-source examples.
