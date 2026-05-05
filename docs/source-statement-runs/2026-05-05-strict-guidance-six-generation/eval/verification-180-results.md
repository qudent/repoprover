# Source-statement generation verification

- Generated at: `2026-05-05T07:54:42.515942+00:00`
- Run output: `docs/source-statement-runs/2026-05-05-strict-guidance-six-generation`
- Work root: `/tmp/repoprover-strict-guidance-six-verify`
- Workers: `1`
- Records: 6
- Successes: 2
- Success rate: 33.3%
- Failure classes: `{"generated_lean_does_not_compile": 3, "grader_gold_statement_not_proved": 1}`

| # | Result | Record | Generated name | Failure |
|---:|---|---|---|---|
| 1 | PASS | `AlgebraicCombinatorics/Details/Limits.lean:PowerSeries.isSummable_of_coeffStabilizesTo_partial_sum'` | `isSummable_of_partial_sum_coeffStabilizesTo` | `` |
| 2 | FAIL | `AlgebraicCombinatorics/DividingFPS.lean:AlgebraicCombinatorics.fps_newtonBinomial_neg` | `fps_newton_binom` | `generated_lean_does_not_compile` |
| 3 | FAIL | `AlgebraicCombinatorics/FPS/Substitution.lean:AlgebraicCombinatorics.fps_comp_coeff_finite` | `fps_comp_coeff_finite` | `generated_lean_does_not_compile` |
| 4 | PASS | `AlgebraicCombinatorics/Partitions/Basics.lean:Nat.Partition.parts_eq_zero_of_partition_zero` | `partition_of_zero_parts_empty` | `` |
| 5 | FAIL | `AlgebraicCombinatorics/Permutations/Basics.lean:AlgebraicCombinatorics.perm_pow_succ` | `perm_pow_apply_eq_iterate` | `grader_gold_statement_not_proved` |
| 6 | FAIL | `AlgebraicCombinatorics/Permutations/Basics.lean:AlgebraicCombinatorics.simpleTransposition_isSwap` | `simpleTransposition_isSwap` | `generated_lean_does_not_compile` |
