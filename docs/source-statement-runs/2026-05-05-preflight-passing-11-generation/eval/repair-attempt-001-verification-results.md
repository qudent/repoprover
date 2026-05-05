# Source-statement generation verification

- Generated at: `2026-05-05T06:59:12.679833+00:00`
- Run output: `docs/source-statement-runs/2026-05-05-preflight-passing-11-generation`
- Work root: `/tmp/repoprover-source-statement-verify-preflight-passing-11-repair1`
- Workers: `1`
- Records: 11
- Successes: 2
- Success rate: 18.2%
- Failure classes: `{"generated_lean_does_not_compile": 3, "grader_gold_statement_not_proved": 1, "missing_model_output": 5}`

| # | Result | Record | Generated name | Failure |
|---:|---|---|---|---|
| 1 | FAIL | `AlgebraicCombinatorics/Details/Limits.lean:PowerSeries.isSummable_of_coeffStabilizesTo_partial_sum'` | `` | `missing_model_output` |
| 2 | FAIL | `AlgebraicCombinatorics/DeterminantsBasic.lean:AlgebraicCombinatorics.Det.det_lowerTriangular` | `` | `missing_model_output` |
| 3 | FAIL | `AlgebraicCombinatorics/DividingFPS.lean:AlgebraicCombinatorics.fps_newtonBinomial_neg` | `fps_newton_binom` | `grader_gold_statement_not_proved` |
| 4 | FAIL | `AlgebraicCombinatorics/FPS/InfiniteProducts.lean:PowerSeries.coeffFinitelyDeterminedInProd_of_finite` | `` | `missing_model_output` |
| 5 | PASS | `AlgebraicCombinatorics/FPS/InfiniteProducts.lean:PowerSeries.exists_xn_approximator` | `exists_isXnApproximator_of_multipliable` | `` |
| 6 | PASS | `AlgebraicCombinatorics/FPS/NotationsExamples.lean:AlgebraicCombinatorics.FPS.binom_symm` | `binom_symm` | `` |
| 7 | FAIL | `AlgebraicCombinatorics/FPS/Substitution.lean:AlgebraicCombinatorics.fps_comp_coeff_finite` | `fps_comp_coeff_eq_finset_sum` | `generated_lean_does_not_compile` |
| 8 | FAIL | `AlgebraicCombinatorics/FPSDefinition.lean:AlgebraicCombinatorics.FPS.X_mul_eq_shift` | `` | `missing_model_output` |
| 9 | FAIL | `AlgebraicCombinatorics/Partitions/Basics.lean:Nat.Partition.parts_eq_zero_of_partition_zero` | `size_eq_zero_iff_eq_empty` | `generated_lean_does_not_compile` |
| 10 | FAIL | `AlgebraicCombinatorics/Permutations/Basics.lean:AlgebraicCombinatorics.perm_pow_succ` | `pow_eq_iterate` | `generated_lean_does_not_compile` |
| 11 | FAIL | `AlgebraicCombinatorics/Permutations/Basics.lean:AlgebraicCombinatorics.simpleTransposition_isSwap` | `` | `missing_model_output` |
