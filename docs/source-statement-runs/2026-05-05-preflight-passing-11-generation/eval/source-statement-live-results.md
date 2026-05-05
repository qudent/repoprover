# Source-statement live eval results

- Generated at: `2026-05-05T06:41:03.047508+00:00`
- Model: `deepseek/deepseek-v4-pro`
- Max tokens: `32768`
- Reasoning effort: `high`
- Repair attempts: `0`
- Repair max tokens: `32768`
- Repair reasoning effort: `high`
- Preflight only: `False`
- Generation only: `True`
- Reuse project: `False`
- Concurrency: `3`
- Sample mode: `corpus-spread`
- Global cost cap: `$0.400000`
- Records attempted: 11 / selected 11
- Successes: 0
- Success rate: 0.0%
- Preflight successes: 0 / 0
- Generation successes: 11 / 11
- Actual reported cost: `$0.064531`
- Failure classes: `{}`

Success means: the prompt withheld the target Lean statement/name; the model generated a theorem/lemma; optional repairs used generated-only compiler feedback; and a grader-only copy of the gold statement was proved by `simpa using <generated theorem>`. This is still an oracle source-span benchmark, not full feed-forward segmentation.

| # | Result | Record | Generated name | Cost | Error / Lean output |
|---:|---|---|---|---:|---|
| 1 | FAIL | `AlgebraicCombinatorics/Details/Limits.lean:PowerSeries.isSummable_of_coeffStabilizesTo_partial_sum'` | `summable_and_tsum'_eq_of_coeffStabilizesTo_partial_sum` | $0.004172 |  |
| 2 | FAIL | `AlgebraicCombinatorics/DeterminantsBasic.lean:AlgebraicCombinatorics.Det.det_lowerTriangular` | `det_lowerTriangular` | $0.004275 |  |
| 3 | FAIL | `AlgebraicCombinatorics/DividingFPS.lean:AlgebraicCombinatorics.fps_newtonBinomial_neg` | `fps_newton_binom` | $0.011881 |  |
| 4 | FAIL | `AlgebraicCombinatorics/FPS/InfiniteProducts.lean:PowerSeries.coeffFinitelyDeterminedInProd_of_finite` | `coeffFinitelyDeterminedInProd_of_finite` | $0.003224 |  |
| 5 | FAIL | `AlgebraicCombinatorics/FPS/InfiniteProducts.lean:PowerSeries.exists_xn_approximator` | `exists_isXnApproximator_of_multipliable` | $0.005541 |  |
| 6 | FAIL | `AlgebraicCombinatorics/FPS/NotationsExamples.lean:AlgebraicCombinatorics.FPS.binom_symm` | `binom_symm` | $0.007923 |  |
| 7 | FAIL | `AlgebraicCombinatorics/FPS/Substitution.lean:AlgebraicCombinatorics.fps_comp_coeff_finite` | `fps_comp_coeff_eq_finset_sum` | $0.007307 |  |
| 8 | FAIL | `AlgebraicCombinatorics/FPSDefinition.lean:AlgebraicCombinatorics.FPS.X_mul_eq_shift` | `lem_fps_xa` | $0.004408 |  |
| 9 | FAIL | `AlgebraicCombinatorics/Partitions/Basics.lean:Nat.Partition.parts_eq_zero_of_partition_zero` | `size_eq_zero_iff_eq_empty` | $0.006017 |  |
| 10 | FAIL | `AlgebraicCombinatorics/Permutations/Basics.lean:AlgebraicCombinatorics.perm_pow_succ` | `pow_eq_iterate` | $0.006660 |  |
| 11 | FAIL | `AlgebraicCombinatorics/Permutations/Basics.lean:AlgebraicCombinatorics.simpleTransposition_isSwap` | `simpleTransposition_eq_transposition` | $0.003120 |  |
