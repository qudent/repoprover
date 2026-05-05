# Source-Statement 36-Record Preflight Report

Date: 2026-05-05

## Command

```bash
UV_CACHE_DIR=/tmp/uv-cache-repoprover uv run python scripts/run_source_statement_live_eval.py \
  --output /tmp/repoprover-source-statement-preflight-corpus-spread-36-20260505 \
  --limit 36 \
  --sample-mode corpus-spread \
  --include-record-imports \
  --lake-cache-from algebraic-combinatorics \
  --reuse-project \
  --preflight-only \
  --lean-timeout 90 \
  --concurrency 1
```

## Result

- Paid calls: 0
- Selected records: 36
- Preflight successes: 11/36
- Failure classes:
  `{"verifier_preflight_error": 2, "verifier_preflight_failed": 23}`
- Output tree: `/tmp/repoprover-source-statement-preflight-corpus-spread-36-20260505`
  (`133M`)
- Committed eval artifacts:
  `docs/source-statement-runs/2026-05-05-preflight-corpus-spread-36/eval/`
- Passing queue:
  `docs/source-statement-runs/2026-05-05-preflight-corpus-spread-36/eval/preflight-passing-records.jsonl`
- Estimated max generation cost for the 11 passing records:
  `$0.329978385`

## Passing Records

- `AlgebraicCombinatorics/Details/Limits.lean:PowerSeries.isSummable_of_coeffStabilizesTo_partial_sum'`
- `AlgebraicCombinatorics/DeterminantsBasic.lean:AlgebraicCombinatorics.Det.det_lowerTriangular`
- `AlgebraicCombinatorics/DividingFPS.lean:AlgebraicCombinatorics.fps_newtonBinomial_neg`
- `AlgebraicCombinatorics/FPS/InfiniteProducts.lean:PowerSeries.coeffFinitelyDeterminedInProd_of_finite`
- `AlgebraicCombinatorics/FPS/InfiniteProducts.lean:PowerSeries.exists_xn_approximator`
- `AlgebraicCombinatorics/FPS/NotationsExamples.lean:AlgebraicCombinatorics.FPS.binom_symm`
- `AlgebraicCombinatorics/FPS/Substitution.lean:AlgebraicCombinatorics.fps_comp_coeff_finite`
- `AlgebraicCombinatorics/FPSDefinition.lean:AlgebraicCombinatorics.FPS.X_mul_eq_shift`
- `AlgebraicCombinatorics/Partitions/Basics.lean:Nat.Partition.parts_eq_zero_of_partition_zero`
- `AlgebraicCombinatorics/Permutations/Basics.lean:AlgebraicCombinatorics.perm_pow_succ`
- `AlgebraicCombinatorics/Permutations/Basics.lean:AlgebraicCombinatorics.simpleTransposition_isSwap`

## Interpretation

The wider corpus-spread preflight increases the candidate paid slice from 8 to
11 records without spending OpenRouter budget. The pass rate is still only
30.6%, so verifier/materializer quality remains a bottleneck for whole-corpus
scale.

The failures are now concentrated in:

- Cauchy-Binet/Desnanot-Jacobi determinant records, which still need the
  manual/oracle-assisted diagnostic path already tracked in `STATUS.md`;
- FPS and Laurent records whose copied local context or generated preflight
  target does not yet close cleanly;
- symmetric-function records, including two heavy-import timeouts at 90 seconds.

Next paid gate: run generation-only over the 11 passing records with a hard cap
around `$0.40`, archive all provider outputs first, then verify from the saved
artifacts with the reusable-project verifier.
