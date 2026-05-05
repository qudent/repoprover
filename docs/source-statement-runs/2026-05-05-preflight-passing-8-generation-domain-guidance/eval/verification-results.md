# Source-statement generation verification

- Generated at: `2026-05-05T04:37:55.228754+00:00`
- Run output: `docs/source-statement-runs/2026-05-05-preflight-passing-8-generation-domain-guidance`
- Work root: `/tmp/repoprover-source-statement-verify-domain-guidance-8-serial`
- Workers: `1`
- Records: 8
- Successes: 2
- Success rate: 25.0%
- Failure classes: `{"generated_lean_does_not_compile": 5, "grader_gold_statement_not_proved": 1}`

| # | Result | Record | Generated name | Failure |
|---:|---|---|---|---|
| 1 | FAIL | `AlgebraicCombinatorics/Details/InfiniteProducts2.lean:PowerSeries.comp_prod_infinite` | `subst_tprod` | `generated_lean_does_not_compile` |
| 2 | PASS | `AlgebraicCombinatorics/DeterminantsBasic.lean:AlgebraicCombinatorics.Det.det_swap_cols` | `det_swap_cols` | `` |
| 3 | FAIL | `AlgebraicCombinatorics/FPS/Multivariate.lean:AlgebraicCombinatorics.eq_of_embedUnivInBiv_eq` | `comp_y_coeff` | `generated_lean_does_not_compile` |
| 4 | FAIL | `AlgebraicCombinatorics/FPS/Substitution.lean:AlgebraicCombinatorics.fps_subs_X_right` | `fps_subst_X` | `generated_lean_does_not_compile` |
| 5 | FAIL | `AlgebraicCombinatorics/FPSDefinition.lean:AlgebraicCombinatorics.FPS.coeff_mul_X_pow` | `lem_fps_xa` | `grader_gold_statement_not_proved` |
| 6 | FAIL | `AlgebraicCombinatorics/Partitions/Basics.lean:Nat.Partition.size_eq` | `parts_sum` | `generated_lean_does_not_compile` |
| 7 | FAIL | `AlgebraicCombinatorics/Permutations/Basics.lean:AlgebraicCombinatorics.simpleTransposition_apply_of_ne` | `simpleTransposition_apply_of_ne_ne` | `generated_lean_does_not_compile` |
| 8 | PASS | `AlgebraicCombinatorics/Permutations/Inversions1.lean:AlgebraicCombinatorics.lexLt_irrefl` | `lexLt_irrefl` | `` |
