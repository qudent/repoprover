# Source-statement generation verification

- Generated at: `2026-05-05T05:11:33.019687+00:00`
- Run output: `docs/source-statement-runs/2026-05-05-preflight-passing-8-generation-hard-guidance`
- Work root: `/tmp/repoprover-source-statement-verify-hard-guidance-8-serial`
- Workers: `1`
- Records: 8
- Successes: 2
- Success rate: 25.0%
- Failure classes: `{"generated_lean_does_not_compile": 3, "grader_gold_statement_not_proved": 3}`

| # | Result | Record | Generated name | Failure |
|---:|---|---|---|---|
| 1 | FAIL | `AlgebraicCombinatorics/Details/InfiniteProducts2.lean:PowerSeries.comp_prod_infinite` | `prop_fps_subs_rule_infprod` | `generated_lean_does_not_compile` |
| 2 | FAIL | `AlgebraicCombinatorics/DeterminantsBasic.lean:AlgebraicCombinatorics.Det.det_swap_cols` | `det_swap_cols` | `generated_lean_does_not_compile` |
| 3 | FAIL | `AlgebraicCombinatorics/FPS/Multivariate.lean:AlgebraicCombinatorics.eq_of_embedUnivInBiv_eq` | `prop_fps_mulvar_comp_y_coeff` | `grader_gold_statement_not_proved` |
| 4 | FAIL | `AlgebraicCombinatorics/FPS/Substitution.lean:AlgebraicCombinatorics.fps_subs_X_right` | `fps_subs_X_right` | `generated_lean_does_not_compile` |
| 5 | FAIL | `AlgebraicCombinatorics/FPSDefinition.lean:AlgebraicCombinatorics.FPS.coeff_mul_X_pow` | `lem_fps_xa` | `grader_gold_statement_not_proved` |
| 6 | PASS | `AlgebraicCombinatorics/Partitions/Basics.lean:Nat.Partition.size_eq` | `parts_sum_eq_n` | `` |
| 7 | FAIL | `AlgebraicCombinatorics/Permutations/Basics.lean:AlgebraicCombinatorics.simpleTransposition_apply_of_ne` | `simpleTransposition_apply_of_ne_of_ne` | `grader_gold_statement_not_proved` |
| 8 | PASS | `AlgebraicCombinatorics/Permutations/Inversions1.lean:AlgebraicCombinatorics.lexLt_irrefl` | `irreflexive_lexLt` | `` |
