# Source-statement generation verification

- Generated at: `2026-05-05T06:04:59.613684+00:00`
- Run output: `docs/source-statement-runs/2026-05-05-preflight-passing-8-generation-hard-guidance`
- Work root: `/tmp/repoprover-source-statement-verify-hard-guidance-8-repair5-rows1-4`
- Workers: `1`
- Records: 8
- Successes: 0
- Success rate: 0.0%
- Failure classes: `{"generated_lean_does_not_compile": 1, "grader_gold_statement_not_proved": 1, "missing_model_output": 6}`

| # | Result | Record | Generated name | Failure |
|---:|---|---|---|---|
| 1 | FAIL | `AlgebraicCombinatorics/Details/InfiniteProducts2.lean:PowerSeries.comp_prod_infinite` | `prop_fps_subs_rule_infprod` | `grader_gold_statement_not_proved` |
| 2 | FAIL | `AlgebraicCombinatorics/DeterminantsBasic.lean:AlgebraicCombinatorics.Det.det_swap_cols` | `` | `missing_model_output` |
| 3 | FAIL | `AlgebraicCombinatorics/FPS/Multivariate.lean:AlgebraicCombinatorics.eq_of_embedUnivInBiv_eq` | `` | `missing_model_output` |
| 4 | FAIL | `AlgebraicCombinatorics/FPS/Substitution.lean:AlgebraicCombinatorics.fps_subs_X_right` | `fps_subs_X_right` | `generated_lean_does_not_compile` |
| 5 | FAIL | `AlgebraicCombinatorics/FPSDefinition.lean:AlgebraicCombinatorics.FPS.coeff_mul_X_pow` | `` | `missing_model_output` |
| 6 | FAIL | `AlgebraicCombinatorics/Partitions/Basics.lean:Nat.Partition.size_eq` | `` | `missing_model_output` |
| 7 | FAIL | `AlgebraicCombinatorics/Permutations/Basics.lean:AlgebraicCombinatorics.simpleTransposition_apply_of_ne` | `` | `missing_model_output` |
| 8 | FAIL | `AlgebraicCombinatorics/Permutations/Inversions1.lean:AlgebraicCombinatorics.lexLt_irrefl` | `` | `missing_model_output` |
