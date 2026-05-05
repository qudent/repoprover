# Source-statement generation verification

- Generated at: `2026-05-05T04:52:39.126859+00:00`
- Run output: `docs/source-statement-runs/2026-05-05-preflight-passing-8-generation-domain-guidance`
- Work root: `/tmp/repoprover-source-statement-verify-domain-guidance-8-repair1-serial`
- Workers: `1`
- Records: 8
- Successes: 1
- Success rate: 12.5%
- Failure classes: `{"generated_lean_does_not_compile": 3, "grader_gold_statement_not_proved": 1, "missing_model_output": 3}`

| # | Result | Record | Generated name | Failure |
|---:|---|---|---|---|
| 1 | FAIL | `AlgebraicCombinatorics/Details/InfiniteProducts2.lean:PowerSeries.comp_prod_infinite` | `subst_tprod` | `generated_lean_does_not_compile` |
| 2 | FAIL | `AlgebraicCombinatorics/DeterminantsBasic.lean:AlgebraicCombinatorics.Det.det_swap_cols` | `` | `missing_model_output` |
| 3 | FAIL | `AlgebraicCombinatorics/FPS/Multivariate.lean:AlgebraicCombinatorics.eq_of_embedUnivInBiv_eq` | `comp_y_coeff` | `generated_lean_does_not_compile` |
| 4 | FAIL | `AlgebraicCombinatorics/FPS/Substitution.lean:AlgebraicCombinatorics.fps_subs_X_right` | `fps_subst_X` | `generated_lean_does_not_compile` |
| 5 | FAIL | `AlgebraicCombinatorics/FPSDefinition.lean:AlgebraicCombinatorics.FPS.coeff_mul_X_pow` | `` | `missing_model_output` |
| 6 | PASS | `AlgebraicCombinatorics/Partitions/Basics.lean:Nat.Partition.size_eq` | `sum_parts_eq` | `` |
| 7 | FAIL | `AlgebraicCombinatorics/Permutations/Basics.lean:AlgebraicCombinatorics.simpleTransposition_apply_of_ne` | `simpleTransposition_apply_of_ne_ne` | `grader_gold_statement_not_proved` |
| 8 | FAIL | `AlgebraicCombinatorics/Permutations/Inversions1.lean:AlgebraicCombinatorics.lexLt_irrefl` | `` | `missing_model_output` |
