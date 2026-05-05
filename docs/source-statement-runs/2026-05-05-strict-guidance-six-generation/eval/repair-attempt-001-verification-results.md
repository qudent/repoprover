# Source-statement generation verification

- Generated at: `2026-05-05T08:05:06.010790+00:00`
- Run output: `docs/source-statement-runs/2026-05-05-strict-guidance-six-generation`
- Work root: `/tmp/repoprover-strict-guidance-six-repair-verify`
- Workers: `1`
- Records: 6
- Successes: 1
- Success rate: 16.7%
- Failure classes: `{"generated_lean_does_not_compile": 1, "missing_model_output": 4}`

| # | Result | Record | Generated name | Failure |
|---:|---|---|---|---|
| 1 | FAIL | `AlgebraicCombinatorics/Details/Limits.lean:PowerSeries.isSummable_of_coeffStabilizesTo_partial_sum'` | `` | `missing_model_output` |
| 2 | FAIL | `AlgebraicCombinatorics/DividingFPS.lean:AlgebraicCombinatorics.fps_newtonBinomial_neg` | `fps_newton_binom` | `generated_lean_does_not_compile` |
| 3 | FAIL | `AlgebraicCombinatorics/FPS/Substitution.lean:AlgebraicCombinatorics.fps_comp_coeff_finite` | `` | `missing_model_output` |
| 4 | FAIL | `AlgebraicCombinatorics/Partitions/Basics.lean:Nat.Partition.parts_eq_zero_of_partition_zero` | `` | `missing_model_output` |
| 5 | FAIL | `AlgebraicCombinatorics/Permutations/Basics.lean:AlgebraicCombinatorics.perm_pow_succ` | `` | `missing_model_output` |
| 6 | PASS | `AlgebraicCombinatorics/Permutations/Basics.lean:AlgebraicCombinatorics.simpleTransposition_isSwap` | `simpleTransposition_isSwap` | `` |
