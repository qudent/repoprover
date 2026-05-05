# Source-statement generation verification

- Generated at: `2026-05-05T07:06:18.112565+00:00`
- Run output: `docs/source-statement-runs/2026-05-05-preflight-passing-11-generation`
- Work root: `/tmp/repoprover-source-statement-verify-preflight-passing-11-generation-180`
- Workers: `1`
- Records: 11
- Successes: 3
- Success rate: 27.3%
- Failure classes: `{"generated_lean_does_not_compile": 6, "grader_gold_statement_not_proved": 2}`

| # | Result | Record | Generated name | Failure |
|---:|---|---|---|---|
| 1 | FAIL | `AlgebraicCombinatorics/Details/Limits.lean:PowerSeries.isSummable_of_coeffStabilizesTo_partial_sum'` | `summable_and_tsum'_eq_of_coeffStabilizesTo_partial_sum` | `grader_gold_statement_not_proved` |
| 2 | PASS | `AlgebraicCombinatorics/DeterminantsBasic.lean:AlgebraicCombinatorics.Det.det_lowerTriangular` | `det_lowerTriangular` | `` |
| 3 | FAIL | `AlgebraicCombinatorics/DividingFPS.lean:AlgebraicCombinatorics.fps_newtonBinomial_neg` | `fps_newton_binom` | `generated_lean_does_not_compile` |
| 4 | PASS | `AlgebraicCombinatorics/FPS/InfiniteProducts.lean:PowerSeries.coeffFinitelyDeterminedInProd_of_finite` | `coeffFinitelyDeterminedInProd_of_finite` | `` |
| 5 | FAIL | `AlgebraicCombinatorics/FPS/InfiniteProducts.lean:PowerSeries.exists_xn_approximator` | `exists_isXnApproximator_of_multipliable` | `generated_lean_does_not_compile` |
| 6 | FAIL | `AlgebraicCombinatorics/FPS/NotationsExamples.lean:AlgebraicCombinatorics.FPS.binom_symm` | `binom_symm` | `generated_lean_does_not_compile` |
| 7 | FAIL | `AlgebraicCombinatorics/FPS/Substitution.lean:AlgebraicCombinatorics.fps_comp_coeff_finite` | `fps_comp_coeff_eq_finset_sum` | `generated_lean_does_not_compile` |
| 8 | PASS | `AlgebraicCombinatorics/FPSDefinition.lean:AlgebraicCombinatorics.FPS.X_mul_eq_shift` | `lem_fps_xa` | `` |
| 9 | FAIL | `AlgebraicCombinatorics/Partitions/Basics.lean:Nat.Partition.parts_eq_zero_of_partition_zero` | `size_eq_zero_iff_eq_empty` | `generated_lean_does_not_compile` |
| 10 | FAIL | `AlgebraicCombinatorics/Permutations/Basics.lean:AlgebraicCombinatorics.perm_pow_succ` | `pow_eq_iterate` | `generated_lean_does_not_compile` |
| 11 | FAIL | `AlgebraicCombinatorics/Permutations/Basics.lean:AlgebraicCombinatorics.simpleTransposition_isSwap` | `simpleTransposition_eq_transposition` | `grader_gold_statement_not_proved` |
