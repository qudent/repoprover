# Source-Statement Targeted Guidance Generation Result

Date: 2026-05-05

This records the paid retry over the six remaining failures from the 11-record
source-statement run after adding targeted statement/API guidance.

## Generation

Input records:

`/tmp/repoprover-targeted-guidance-six-failures.jsonl`, selected from rows
1, 3, 7, 9, 10, and 11 of
`docs/source-statement-runs/2026-05-05-preflight-passing-11-generation/eval/selected-records.jsonl`.

Command:

```bash
bash -ic 'UV_CACHE_DIR=/tmp/uv-cache-repoprover uv run python scripts/run_source_statement_live_eval.py \
  --records /tmp/repoprover-targeted-guidance-six-failures.jsonl \
  --output docs/source-statement-runs/2026-05-05-targeted-guidance-six-generation \
  --limit 6 --sample-mode corpus-spread --include-record-imports \
  --lake-cache-from algebraic-combinatorics --generation-only \
  --max-actual-cost-usd 0.25 --concurrency 3 \
  --max-tokens 32768 --reasoning-effort high'
```

Result:

- provider responses: `6/6`
- parsed generations: `6/6`
- paid calls: `6`
- actual reported cost: `$0.03896991`
- provider artifacts committed before verification in commit `af9fc56`

## Serial Verification

Command:

```bash
UV_CACHE_DIR=/tmp/uv-cache-repoprover uv run python scripts/verify_source_statement_generation.py \
  --run-output docs/source-statement-runs/2026-05-05-targeted-guidance-six-generation \
  --work-root /tmp/repoprover-targeted-guidance-six-verify \
  --lake-cache-from algebraic-combinatorics --include-record-imports \
  --workers 1 --lean-timeout 180 --output-prefix verification-180
```

Result:

- verified successes: `0/6`
- failure classes: `generated_lean_does_not_compile=5`,
  `grader_gold_statement_not_proved=1`
- shared work root size after the run: about `26M`
- elapsed wall time from verification artifact timestamps: about 4 minutes

| # | Record | Generated name | Verification result |
|---:|---|---|---|
| 1 | `PowerSeries.isSummable_of_coeffStabilizesTo_partial_sum'` | `sum_lim_conv` | generated-only compiles, but hidden grader fails because the model still bundled `IsSummable ∧ tsum' = L` |
| 2 | `AlgebraicCombinatorics.fps_newtonBinomial_neg` | `newton_binom` | generated-only compile failure; still misuses integer powers/coercions and leaves invalid syntax |
| 3 | `AlgebraicCombinatorics.fps_comp_coeff_finite` | `fps_comp_coeff_finsum_eq_sum` | generated-only compile failure; invalid `finsum`/binder syntax |
| 4 | `Nat.Partition.parts_eq_zero_of_partition_zero` | `empty_unique` | generated-only compile failure; uses unavailable `eq_iff_parts_eq` in the Mathlib-only prompt context |
| 5 | `AlgebraicCombinatorics.perm_pow_succ` | `pow_eq_iterate` | generated-only compile failure; still treats function powers incorrectly |
| 6 | `AlgebraicCombinatorics.simpleTransposition_isSwap` | `simpleTransposition_isSwap` | generated-only compile failure; targets `IsSwap` but invents unavailable `Equiv.swap_isSwap` |

## Interpretation

The targeted guidance made the prompts more explicit but did not improve the
verified score. This is useful negative evidence: for these rows, broad textual
guidance is not enough. The next iteration should materialize the exact visible
API examples needed for the row, or use a stricter output contract that asks for
only the expected statement shape before asking for a proof.

The serial verifier was not the bottleneck in this run. With a reusable Lean
work root and `workers=1`, it produced individual failure signals for all six
rows in a few minutes and used only tens of megabytes of scratch space.
