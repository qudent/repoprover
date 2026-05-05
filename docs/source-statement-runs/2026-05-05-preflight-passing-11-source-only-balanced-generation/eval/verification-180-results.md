# Source-statement generation verification

- Generated at: `2026-05-05T10:47:21.037793+00:00`
- Run output: `docs/source-statement-runs/2026-05-05-preflight-passing-11-source-only-balanced-generation`
- Work root: `/tmp/repoprover-source-only-balanced-11-verify`
- Workers: `1`
- Records: 11
- Successes: 1
- Success rate: 9.1%
- Failure classes: `{"forbidden_placeholder": 1, "generated_lean_does_not_compile": 6, "grader_gold_statement_not_proved": 3}`

| # | Result | Record | Generated name | Failure |
|---:|---|---|---|---|
| 1 | FAIL | `AlgebraicCombinatorics/Details/Limits.lean:PowerSeries.isSummable_of_coeffStabilizesTo_partial_sum'` | `sum_lim_conv` | `generated_lean_does_not_compile` |
| 2 | FAIL | `AlgebraicCombinatorics/DeterminantsBasic.lean:AlgebraicCombinatorics.Det.det_lowerTriangular` | `det_triang` | `grader_gold_statement_not_proved` |
| 3 | FAIL | `AlgebraicCombinatorics/DividingFPS.lean:AlgebraicCombinatorics.fps_newtonBinomial_neg` | `fps_newton_binom` | `generated_lean_does_not_compile` |
| 4 | FAIL | `AlgebraicCombinatorics/FPS/InfiniteProducts.lean:PowerSeries.coeffFinitelyDeterminedInProd_of_finite` | `CoeffFinitelyDeterminedInSum` | `grader_gold_statement_not_proved` |
| 5 | FAIL | `AlgebraicCombinatorics/FPS/InfiniteProducts.lean:PowerSeries.exists_xn_approximator` | `exists_isXnApproximator_of_multipliable` | `generated_lean_does_not_compile` |
| 6 | FAIL | `AlgebraicCombinatorics/FPS/NotationsExamples.lean:AlgebraicCombinatorics.FPS.binom_symm` | `binom_sym` | `forbidden_placeholder` |
| 7 | FAIL | `AlgebraicCombinatorics/FPS/Substitution.lean:AlgebraicCombinatorics.fps_comp_coeff_finite` | `fps_subst_eq_tsum` | `generated_lean_does_not_compile` |
| 8 | PASS | `AlgebraicCombinatorics/FPSDefinition.lean:AlgebraicCombinatorics.FPS.X_mul_eq_shift` | `X_mul_eq` | `` |
| 9 | FAIL | `AlgebraicCombinatorics/Partitions/Basics.lean:Nat.Partition.parts_eq_zero_of_partition_zero` | `card_partitions_of_5` | `generated_lean_does_not_compile` |
| 10 | FAIL | `AlgebraicCombinatorics/Permutations/Basics.lean:AlgebraicCombinatorics.perm_pow_succ` | `card_perm` | `generated_lean_does_not_compile` |
| 11 | FAIL | `AlgebraicCombinatorics/Permutations/Basics.lean:AlgebraicCombinatorics.simpleTransposition_isSwap` | `simpleTransposition_eq_transposition` | `grader_gold_statement_not_proved` |
