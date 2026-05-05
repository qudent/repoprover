# Source-Statement 11-Record Generation Results

Date: 2026-05-05

## Inputs

Passing queue from the zero-cost 36-record preflight:
`docs/source-statement-runs/2026-05-05-preflight-corpus-spread-36/eval/preflight-passing-records.jsonl`

Paid run artifacts:
`docs/source-statement-runs/2026-05-05-preflight-passing-11-generation`

## Generation

Command shape:

```bash
UV_CACHE_DIR=/tmp/uv-cache-repoprover uv run python scripts/run_source_statement_live_eval.py \
  --records docs/source-statement-runs/2026-05-05-preflight-corpus-spread-36/eval/preflight-passing-records.jsonl \
  --output docs/source-statement-runs/2026-05-05-preflight-passing-11-generation \
  --limit 11 --sample-mode corpus-spread --include-record-imports \
  --lake-cache-from algebraic-combinatorics --generation-only \
  --max-actual-cost-usd 0.40 --concurrency 3 \
  --max-tokens 32768 --reasoning-effort high
```

- Paid calls: 11
- Parsed generations: 11/11
- Actual reported OpenRouter cost: `$0.064530713`
- Initial serial verification at 90s: 3/11 successes, plus one verifier timeout
- Reverification at 180s: 3/11 successes, with row 1 reclassified as a hidden
  grader mismatch instead of infrastructure timeout

## Repairs

Repair attempt 1 targeted the six generated-only compile failures from the
initial verification:

- Paid calls: 6
- Actual reported cost: `$0.035276934`
- Verified repair successes: 2/6 (`exists_xn_approximator`, `binom_symm`)

Repair attempt 2 targeted the three remaining generated-only compile failures
from attempt 1:

- Paid calls: 3
- Actual reported cost: `$0.087395850`
- Verified repair successes: 0/3

Total generation plus repairs for this 11-record slice: `$0.187203497`.

## Cumulative Result

| # | Record | First pass | Repair 1 | Repair 2 | Best result | Remaining issue |
|---:|---|---|---|---|---|---|
| 1 | `PowerSeries.isSummable_of_coeffStabilizesTo_partial_sum'` | FAIL | n/a | n/a | FAIL | Generated theorem compiles after 180s verifier timeout, but does not imply the hidden target statement. |
| 2 | `AlgebraicCombinatorics.Det.det_lowerTriangular` | PASS | n/a | n/a | PASS |  |
| 3 | `AlgebraicCombinatorics.fps_newtonBinomial_neg` | FAIL | FAIL | n/a | FAIL | Repair compiles but still misses the hidden target statement. |
| 4 | `PowerSeries.coeffFinitelyDeterminedInProd_of_finite` | PASS | n/a | n/a | PASS |  |
| 5 | `PowerSeries.exists_xn_approximator` | FAIL | PASS | n/a | PASS |  |
| 6 | `AlgebraicCombinatorics.FPS.binom_symm` | FAIL | PASS | n/a | PASS |  |
| 7 | `AlgebraicCombinatorics.fps_comp_coeff_finite` | FAIL | FAIL | FAIL | FAIL | Still fails generated-only Lean after two compiler-feedback repairs. |
| 8 | `AlgebraicCombinatorics.FPS.X_mul_eq_shift` | PASS | n/a | n/a | PASS |  |
| 9 | `Nat.Partition.parts_eq_zero_of_partition_zero` | FAIL | FAIL | FAIL | FAIL | Still fails generated-only Lean after two compiler-feedback repairs. |
| 10 | `AlgebraicCombinatorics.perm_pow_succ` | FAIL | FAIL | FAIL | FAIL | Still fails generated-only Lean after two compiler-feedback repairs. |
| 11 | `AlgebraicCombinatorics.simpleTransposition_isSwap` | FAIL | n/a | n/a | FAIL | Generated theorem compiles but does not match the hidden target shape. |

Best cumulative result: 5/11 verified successes.

## Interpretation

The wider slice validates that the decoupled pipeline scales operationally:
preflight, provider generation, verification, and repair all produced durable
per-record artifacts. Quality is not yet high enough for feed-forward textbook
formalization: the 6/8 hard-guidance slice was easier after targeted diagnostics,
while this broader 11-record slice reaches only 5/11 after two repair passes.

The next no/low-cost step should classify the 6 remaining failures by visible
statement-shape diagnostics and local API families before another paid retry.
The repair budget should not keep retrying rows 7, 9, and 10 without more
specific context, since a second compiler-feedback pass did not improve them.
