# Source-statement generation verification

- Generated at: `2026-05-05T07:38:29.358246+00:00`
- Run output: `docs/source-statement-runs/2026-05-05-targeted-guidance-six-generation`
- Work root: `/tmp/repoprover-targeted-guidance-six-verify`
- Workers: `1`
- Records: 6
- Successes: 0
- Success rate: 0.0%
- Failure classes: `{"generated_lean_does_not_compile": 5, "grader_gold_statement_not_proved": 1}`

| # | Result | Record | Generated name | Failure |
|---:|---|---|---|---|
| 1 | FAIL | `AlgebraicCombinatorics/Details/Limits.lean:PowerSeries.isSummable_of_coeffStabilizesTo_partial_sum'` | `sum_lim_conv` | `grader_gold_statement_not_proved` |
| 2 | FAIL | `AlgebraicCombinatorics/DividingFPS.lean:AlgebraicCombinatorics.fps_newtonBinomial_neg` | `newton_binom` | `generated_lean_does_not_compile` |
| 3 | FAIL | `AlgebraicCombinatorics/FPS/Substitution.lean:AlgebraicCombinatorics.fps_comp_coeff_finite` | `fps_comp_coeff_finsum_eq_sum` | `generated_lean_does_not_compile` |
| 4 | FAIL | `AlgebraicCombinatorics/Partitions/Basics.lean:Nat.Partition.parts_eq_zero_of_partition_zero` | `empty_unique` | `generated_lean_does_not_compile` |
| 5 | FAIL | `AlgebraicCombinatorics/Permutations/Basics.lean:AlgebraicCombinatorics.perm_pow_succ` | `pow_eq_iterate` | `generated_lean_does_not_compile` |
| 6 | FAIL | `AlgebraicCombinatorics/Permutations/Basics.lean:AlgebraicCombinatorics.simpleTransposition_isSwap` | `simpleTransposition_isSwap` | `generated_lean_does_not_compile` |
