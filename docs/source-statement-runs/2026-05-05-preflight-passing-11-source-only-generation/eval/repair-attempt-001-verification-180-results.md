# Source-statement generation verification

- Generated at: `2026-05-05T10:17:06.514869+00:00`
- Run output: `docs/source-statement-runs/2026-05-05-preflight-passing-11-source-only-generation`
- Work root: `/tmp/repoprover-source-only-11-repair-verify`
- Workers: `1`
- Records: 7
- Successes: 3
- Success rate: 42.9%
- Failure classes: `{"generated_lean_does_not_compile": 3, "grader_gold_statement_not_proved": 1}`

| # | Result | Record | Generated name | Failure |
|---:|---|---|---|---|
| 3 | PASS | `AlgebraicCombinatorics/DividingFPS.lean:AlgebraicCombinatorics.fps_newtonBinomial_neg` | `fps_onePlusX_pow_int` | `` |
| 4 | FAIL | `AlgebraicCombinatorics/FPS/InfiniteProducts.lean:PowerSeries.coeffFinitelyDeterminedInProd_of_finite` | `coeff_finitely_determined_iff` | `generated_lean_does_not_compile` |
| 5 | PASS | `AlgebraicCombinatorics/FPS/InfiniteProducts.lean:PowerSeries.exists_xn_approximator` | `exists_isXnApproximator_of_multipliable` | `` |
| 6 | PASS | `AlgebraicCombinatorics/FPS/NotationsExamples.lean:AlgebraicCombinatorics.FPS.binom_symm` | `binom_sym` | `` |
| 7 | FAIL | `AlgebraicCombinatorics/FPS/Substitution.lean:AlgebraicCombinatorics.fps_comp_coeff_finite` | `summable_fps_comp` | `grader_gold_statement_not_proved` |
| 9 | FAIL | `AlgebraicCombinatorics/Partitions/Basics.lean:Nat.Partition.parts_eq_zero_of_partition_zero` | `partition_weakly_decreasing_finite` | `generated_lean_does_not_compile` |
| 10 | FAIL | `AlgebraicCombinatorics/Permutations/Basics.lean:AlgebraicCombinatorics.perm_pow_succ` | `card_perm` | `generated_lean_does_not_compile` |
