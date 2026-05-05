# Source-statement generation verification

- Generated at: `2026-05-05T08:14:41.399406+00:00`
- Run output: `docs/source-statement-runs/2026-05-05-strict-guidance-six-generation`
- Work root: `/tmp/repoprover-strict-guidance-six-shape-repair-verify`
- Workers: `1`
- Records: 6
- Successes: 0
- Success rate: 0.0%
- Failure classes: `{"grader_gold_statement_not_proved": 1, "missing_model_output": 5}`

| # | Result | Record | Generated name | Failure |
|---:|---|---|---|---|
| 1 | FAIL | `AlgebraicCombinatorics/Details/Limits.lean:PowerSeries.isSummable_of_coeffStabilizesTo_partial_sum'` | `` | `missing_model_output` |
| 2 | FAIL | `AlgebraicCombinatorics/DividingFPS.lean:AlgebraicCombinatorics.fps_newtonBinomial_neg` | `` | `missing_model_output` |
| 3 | FAIL | `AlgebraicCombinatorics/FPS/Substitution.lean:AlgebraicCombinatorics.fps_comp_coeff_finite` | `` | `missing_model_output` |
| 4 | FAIL | `AlgebraicCombinatorics/Partitions/Basics.lean:Nat.Partition.parts_eq_zero_of_partition_zero` | `` | `missing_model_output` |
| 5 | FAIL | `AlgebraicCombinatorics/Permutations/Basics.lean:AlgebraicCombinatorics.perm_pow_succ` | `perm_pow_succ` | `grader_gold_statement_not_proved` |
| 6 | FAIL | `AlgebraicCombinatorics/Permutations/Basics.lean:AlgebraicCombinatorics.simpleTransposition_isSwap` | `` | `missing_model_output` |
