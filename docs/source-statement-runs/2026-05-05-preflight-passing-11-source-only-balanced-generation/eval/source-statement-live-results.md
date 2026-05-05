# Source-statement live eval results

- Generated at: `2026-05-05T10:40:03.776327+00:00`
- Model: `deepseek/deepseek-v4-pro`
- Max tokens: `32768`
- Reasoning effort: `high`
- Repair attempts: `0`
- Repair max tokens: `32768`
- Repair reasoning effort: `high`
- Context mode: `source-only`
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
- Generation successes: 10 / 10
- Actual reported cost: `$0.126677`
- Failure classes: `{"forbidden_placeholder": 1}`

Success means: the prompt withheld the target Lean statement/name; the model generated a theorem/lemma; optional repairs used generated-only compiler feedback; and a grader-only copy of the gold statement was proved by `simpa using <generated theorem>`. This is still an oracle source-span benchmark, not full feed-forward segmentation.

| # | Result | Record | Generated name | Cost | Error / Lean output |
|---:|---|---|---|---:|---|
| 1 | FAIL | `AlgebraicCombinatorics/Details/Limits.lean:PowerSeries.isSummable_of_coeffStabilizesTo_partial_sum'` | `sum_lim_conv` | $0.038541 |  |
| 2 | FAIL | `AlgebraicCombinatorics/DeterminantsBasic.lean:AlgebraicCombinatorics.Det.det_lowerTriangular` | `det_triang` | $0.005008 |  |
| 3 | FAIL | `AlgebraicCombinatorics/DividingFPS.lean:AlgebraicCombinatorics.fps_newtonBinomial_neg` | `fps_newton_binom` | $0.019608 |  |
| 4 | FAIL | `AlgebraicCombinatorics/FPS/InfiniteProducts.lean:PowerSeries.coeffFinitelyDeterminedInProd_of_finite` | `CoeffFinitelyDeterminedInSum` | $0.007560 |  |
| 5 | FAIL | `AlgebraicCombinatorics/FPS/InfiniteProducts.lean:PowerSeries.exists_xn_approximator` | `exists_isXnApproximator_of_multipliable` | $0.005200 |  |
| 6 | FAIL | `AlgebraicCombinatorics/FPS/NotationsExamples.lean:AlgebraicCombinatorics.FPS.binom_symm` | `binom_sym` | $0.014744 | ValueError: model output contains forbidden placeholder |
| 7 | FAIL | `AlgebraicCombinatorics/FPS/Substitution.lean:AlgebraicCombinatorics.fps_comp_coeff_finite` | `fps_subst_eq_tsum` | $0.014112 |  |
| 8 | FAIL | `AlgebraicCombinatorics/FPSDefinition.lean:AlgebraicCombinatorics.FPS.X_mul_eq_shift` | `X_mul_eq` | $0.004073 |  |
| 9 | FAIL | `AlgebraicCombinatorics/Partitions/Basics.lean:Nat.Partition.parts_eq_zero_of_partition_zero` | `card_partitions_of_5` | $0.008706 |  |
| 10 | FAIL | `AlgebraicCombinatorics/Permutations/Basics.lean:AlgebraicCombinatorics.perm_pow_succ` | `card_perm` | $0.003638 |  |
| 11 | FAIL | `AlgebraicCombinatorics/Permutations/Basics.lean:AlgebraicCombinatorics.simpleTransposition_isSwap` | `simpleTransposition_eq_transposition` | $0.005487 |  |
