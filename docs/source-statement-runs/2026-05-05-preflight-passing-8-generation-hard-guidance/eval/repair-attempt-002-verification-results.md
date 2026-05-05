# Source-statement generation verification

- Generated at: `2026-05-05T05:40:01.151275+00:00`
- Run output: `docs/source-statement-runs/2026-05-05-preflight-passing-8-generation-hard-guidance`
- Work root: `/tmp/repoprover-source-statement-verify-hard-guidance-8-shape-repair2`
- Workers: `1`
- Records: 8
- Successes: 3
- Success rate: 37.5%
- Failure classes: `{"generated_lean_does_not_compile": 1, "missing_model_output": 4}`

| # | Result | Record | Generated name | Failure |
|---:|---|---|---|---|
| 1 | FAIL | `AlgebraicCombinatorics/Details/InfiniteProducts2.lean:PowerSeries.comp_prod_infinite` | `` | `missing_model_output` |
| 2 | FAIL | `AlgebraicCombinatorics/DeterminantsBasic.lean:AlgebraicCombinatorics.Det.det_swap_cols` | `` | `missing_model_output` |
| 3 | PASS | `AlgebraicCombinatorics/FPS/Multivariate.lean:AlgebraicCombinatorics.eq_of_embedUnivInBiv_eq` | `prop_fps_mulvar_comp_y_coeff` | `` |
| 4 | FAIL | `AlgebraicCombinatorics/FPS/Substitution.lean:AlgebraicCombinatorics.fps_subs_X_right` | `fps_subs_X_right` | `generated_lean_does_not_compile` |
| 5 | PASS | `AlgebraicCombinatorics/FPSDefinition.lean:AlgebraicCombinatorics.FPS.coeff_mul_X_pow` | `lem_fps_xa` | `` |
| 6 | FAIL | `AlgebraicCombinatorics/Partitions/Basics.lean:Nat.Partition.size_eq` | `` | `missing_model_output` |
| 7 | PASS | `AlgebraicCombinatorics/Permutations/Basics.lean:AlgebraicCombinatorics.simpleTransposition_apply_of_ne` | `simpleTransposition_apply_of_ne_of_ne` | `` |
| 8 | FAIL | `AlgebraicCombinatorics/Permutations/Inversions1.lean:AlgebraicCombinatorics.lexLt_irrefl` | `` | `missing_model_output` |
