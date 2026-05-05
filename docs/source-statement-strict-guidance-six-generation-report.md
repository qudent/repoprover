# Source-Statement Strict Guidance Generation Result

Date: 2026-05-05

This records the paid retry after tightening prompt constraints from the 0/6
targeted-guidance run.

## Generation

Command:

```bash
bash -ic 'UV_CACHE_DIR=/tmp/uv-cache-repoprover uv run python scripts/run_source_statement_live_eval.py \
  --records /tmp/repoprover-targeted-guidance-six-failures.jsonl \
  --output docs/source-statement-runs/2026-05-05-strict-guidance-six-generation \
  --limit 6 --sample-mode corpus-spread --include-record-imports \
  --lake-cache-from algebraic-combinatorics --generation-only \
  --max-actual-cost-usd 0.25 --concurrency 3 \
  --max-tokens 32768 --reasoning-effort high'
```

Result:

- provider responses: `6/6`
- parsed generations: `6/6`
- paid calls: `6`
- actual reported cost: `$0.0308386`
- provider artifacts committed before verification in commit `e123672`

## Serial Verification

Command:

```bash
UV_CACHE_DIR=/tmp/uv-cache-repoprover uv run python scripts/verify_source_statement_generation.py \
  --run-output docs/source-statement-runs/2026-05-05-strict-guidance-six-generation \
  --work-root /tmp/repoprover-strict-guidance-six-verify \
  --lake-cache-from algebraic-combinatorics --include-record-imports \
  --workers 1 --lean-timeout 180 --output-prefix verification-180
```

Result:

- verified successes: `2/6`
- failure classes: `generated_lean_does_not_compile=3`,
  `grader_gold_statement_not_proved=1`

| # | Record | Generated name | Result |
|---:|---|---|---|
| 1 | `PowerSeries.isSummable_of_coeffStabilizesTo_partial_sum'` | `isSummable_of_partial_sum_coeffStabilizesTo` | PASS |
| 2 | `AlgebraicCombinatorics.fps_newtonBinomial_neg` | `fps_newton_binom` | compile failure: integer power/coercion misuse and failed `lift` tactic |
| 3 | `AlgebraicCombinatorics.fps_comp_coeff_finite` | `fps_comp_coeff_finite` | compile failure: support-subset proof leaves `d ≤ n` unsolved |
| 4 | `Nat.Partition.parts_eq_zero_of_partition_zero` | `partition_of_zero_parts_empty` | PASS |
| 5 | `AlgebraicCombinatorics.perm_pow_succ` | `perm_pow_apply_eq_iterate` | generated-only compiles, but hidden grader fails because the model still chose pointwise iteration instead of the group-power statement |
| 6 | `AlgebraicCombinatorics.simpleTransposition_isSwap` | `simpleTransposition_isSwap` | compile failure: close to the right `IsSwap` shape, but `omega` cannot prove one `Fin` bound |

## Interpretation

The stricter source-comment-derived constraints recovered two of the six hard
rows and confirmed that prompt shape matters. The remaining failures no longer
justify another fresh broad-generation pass:

- rows 2, 3, and 6 are generated-only compile failures and are candidates for a
  single compiler-feedback repair pass;
- row 5 is a statement-shape mismatch and needs a statement-shape-first stage or
  stronger direct source-comment contract, not compiler repair.

This also continues to support the queue design: provider generation, artifact
logging, and serial Lean verification are operationally decoupled.
