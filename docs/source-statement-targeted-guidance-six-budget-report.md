# Source-Statement Targeted Guidance Budget Check

Date: 2026-05-05

This records the zero-cost prompt validation for the six remaining failures from
`docs/source-statement-preflight-passing-11-failure-diagnosis.md`.

## Change

`scripts/run_source_statement_live_eval.py` now emits targeted
statement-shape/API guidance for the remaining 11-record failure buckets:

- FPS limits: avoid bundling `IsSummable f` with a `tsum'` equality unless the
  source focus asks for the combined theorem.
- Negative-binomial FPS: keep the local binder/typeclass shape
  `{F : Type*} [Field F] [BinomialRing F] (n : ℕ)` and the coefficient family
  `Ring.choose (-(n : ℤ)) k : F`.
- FPS substitution finite coefficients: use `fps_comp_coeff`,
  `finsum_eq_sum_of_support_subset`, and the `fps_subs_wd_firstCoeffs` support
  proof shape instead of guessed finite-sum helpers.
- Partition zero: use `p.parts`, `partition_zero_parts`,
  available cardinality facts, and `eq_iff_parts_eq` instead of invented
  `.entries`/`.sum_eq` fields.
- Permutation powers: use current `Equiv.Perm`/function-coercion APIs such as
  `Equiv.Perm.coe_mul`, `Equiv.Perm.mul_apply`, and `Function.comp_apply`.
- Simple transposition swap shape: state `(simpleTransposition i).IsSwap` when
  the source asks that the simple transposition is a swap, not only equality to a
  transposition.

The guidance avoids exposing the hidden target declaration names in the emitted
prompt payloads.

## Zero-Cost Validation

Command:

```bash
awk 'NR==1 || NR==3 || NR==7 || NR==9 || NR==10 || NR==11 {print}' \
  docs/source-statement-runs/2026-05-05-preflight-passing-11-generation/eval/selected-records.jsonl \
  > /tmp/repoprover-targeted-guidance-six-failures.jsonl

UV_CACHE_DIR=/tmp/uv-cache-repoprover uv run python scripts/run_source_statement_live_eval.py \
  --records /tmp/repoprover-targeted-guidance-six-failures.jsonl \
  --output docs/source-statement-runs/2026-05-05-targeted-guidance-six-budget \
  --limit 6 --sample-mode corpus-spread --include-record-imports \
  --budget-only --max-tokens 32768 --reasoning-effort high
```

Result:

- records completed: `6`
- paid calls made: `0`
- actual cost: `$0.00`
- output size: `192K`
- estimated max one-shot generation cost for these six rows: `$0.180379275`

Mechanical prompt checks:

- row 1 includes `Do not bundle IsSummable f`;
- row 3 includes `fps_onePlusX_pow_neg'`;
- row 7 includes `finsum_eq_sum_of_support_subset`;
- row 9 includes `partition_zero_parts`;
- row 10 includes `Equiv.Perm.coe_mul`;
- row 11 includes `(simpleTransposition i).IsSwap`;
- the emitted payloads do not contain hidden target names
  `fps_newtonBinomial_neg`, `fps_comp_coeff_finite`,
  `parts_eq_zero_of_partition_zero`, `perm_pow_succ`, or
  `simpleTransposition_isSwap`.

Focused tests:

```bash
UV_CACHE_DIR=/tmp/uv-cache-repoprover uv run pytest \
  tests/test_source_statement_live_eval.py \
  tests/test_source_statement_generation_artifacts.py \
  tests/test_minimal_context_smoke_materializer.py
```

Result: `59 passed`.

## Interpretation

This is a prompt/context checkpoint, not a quality result. It justifies one
small paid generation-only retry on the same six rows before spending on a wider
slice. The retry should keep provider calls decoupled from Lean verification and
archive every provider response before checking.
