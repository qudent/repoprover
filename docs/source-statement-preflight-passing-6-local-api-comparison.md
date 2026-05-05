# Source-Statement Preflight-Passing Six Local API Comparison

Date: 2026-05-05

## Generation Run

Artifacts:
`docs/source-statement-runs/2026-05-05-preflight-passing-6-generation-local-api`

Command shape:

```bash
UV_CACHE_DIR=/tmp/uv-cache-repoprover uv run python scripts/run_source_statement_live_eval.py \
  --records /tmp/repoprover-source-statement-preflight-passing-6.jsonl \
  --output docs/source-statement-runs/2026-05-05-preflight-passing-6-generation-local-api \
  --limit 6 \
  --sample-mode corpus-spread \
  --include-record-imports \
  --lake-cache-from algebraic-combinatorics \
  --generation-only \
  --openrouter-timeout 240 \
  --max-actual-cost-usd 0.25 \
  --concurrency 3
```

Result:

- Paid calls: 6
- Parsed generation artifacts: 6/6
- Actual reported OpenRouter cost: `$0.041165848`
- Lean verification during provider calls: none

## Verification

Serial reusable-project verification:

```bash
UV_CACHE_DIR=/tmp/uv-cache-repoprover uv run python scripts/verify_source_statement_generation.py \
  --run-output docs/source-statement-runs/2026-05-05-preflight-passing-6-generation-local-api \
  --work-root /tmp/repoprover-source-statement-verify-local-api-serial \
  --lake-cache-from algebraic-combinatorics \
  --include-record-imports \
  --workers 1 \
  --lean-timeout 90
```

Result:

- Records considered: 6
- Successes: 0
- Failure classes:
  - `generated_lean_does_not_compile`: 5
  - `grader_gold_statement_not_proved`: 1
- Verifier worktree size: about `20M`
- Archived run directory size: about `408K`

## Row Notes

| # | Record | Generated name | Failure | Note |
|---:|---|---|---|---|
| 1 | `PowerSeries.coeffStabilizesTo_partial_sum'` | `sum_lim` | compile | Introduced a topological `HasSum` statement without the needed `TopologicalSpace K⟦X⟧` instance. |
| 2 | `AlgebraicCombinatorics.Det.det_swap_cols` | `det_swap_cols` | compile | Used retrieved `det_swap_rows`, but the transpose/submatrix rewrite did not match. |
| 3 | `AlgebraicCombinatorics.Det.det_add_smul_col` | `det_colop` | compile | Still bundled the column swap and add-smul column facts; generated transpose/update proof left goals. |
| 4 | `AlgebraicCombinatorics.FPS.pascal_identity_succ` | `binom_rec` | grader mismatch | Compiled by calling retrieved `pascal_identity`, but formalized the Nat theorem rather than the generalized `Ring.choose` theorem. |
| 5 | `AlgebraicCombinatorics.FPS.X_coeff_one` | `coeff_X_fps` | compile | Nearly right statement shape, but proof `by simp` made no progress. |
| 6 | `Nat.Partition.partsCount_eq_largestPartCount` | `partsCount_eq_card_largestPart` | compile | Invented unavailable `Finset.card_congr`; proof script then had no goals. |

## Comparison

Local API retrieval changed model behavior in useful ways: the determinant and
binomial generations now cite retrieved local declarations instead of only
inventing names. It did not produce a passing row on this six-record slice.

The remaining failures are narrower than the earlier broad missing-API failures:
most are now ordinary proof-repair failures or exact-statement selection
failures. The next useful iteration should be a generated-only repair queue over
the five compile failures, with compiler output plus the same retrieved local API
context, and a stricter source-focus rule for generalized binomial records.

Serial Lean verification remains adequate here. It checked every row
individually, produced meaningful failure classes, and used a small reusable
project tree; it is not the bottleneck relative to prompt/context quality.
