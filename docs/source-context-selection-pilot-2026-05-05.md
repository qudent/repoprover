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

## Source-Progress and Project-Context Follow-Up

Later runs added two generic context fixes:

- `source_progress_context.prior_same_label_declarations` tells the selector
  which same-file lettered parts are already formalized before the target.
- `source_progress_context.imported_source_label_declarations` exposes previous
  formalized project statements from imported modules when they reference the
  visible source label.

The source-progress selector run:

`docs/source-statement-runs/2026-05-05-context-selection-source-progress-paid/`

cost `$0.002214212`. It selected only
`lem.sf.alternant-0 part (b)` for `alternant_swap`, because part (a) was already
formalized as `alternant_zero_of_eq`. The follow-up generation run:

`docs/source-statement-runs/2026-05-05-source-progress-context-selected-generation-paid/`

cost `$0.041659341` and generated the right narrow theorem shape for
`alternant_swap`, but verification still passed `0/2`. A generic materializer
fix now restores active `noncomputable section` commands; this removed the first
alternant compiler blocker, leaving a generation issue around explicit
polymorphic arguments.

The project-context selector run:

`docs/source-statement-runs/2026-05-05-context-selection-project-context-paid/`

cost `$0.002581152`. It selected `alternant_swap` part (b), identified imported
`AlgebraicCombinatorics.SymmetricFunctions.LittlewoodRichardson.alternant_swap`
as the direct previous-project theorem, and kept unexplained payload target-name
leaks at `0`. The audit records one allowed previous-project name overlap because
the imported theorem has the same local name as the wrapper target.

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
- Source-part disambiguation is now working on the alternant broad-label case;
  the next proof-generation run should apply previous-project context before
  trying to reprove long imported facts.

## Next Steps

1. Apply the project-context selector output to records and run a generation-only
   probe, committing paid artifacts before Lean verification.
2. Reduce selector schema verbosity so 4-record batches can finish in JSON.
3. Split selection into two compact rounds if the combined schema remains too
   verbose: source-part/project-context selection first, Mathlib API selection
   second.
4. Expand beyond the current two-record probe only after the
   context-selection-to-proof path succeeds on at least one broad-label example.
