# Source-statement shape diagnostic

- Generated at: `2026-05-05T05:29:28.217101+00:00`
- Run output: `docs/source-statement-runs/2026-05-05-preflight-passing-8-generation-hard-guidance`
- Payload artifact: `openrouter-payload.json`
- Model artifact: `model-output.json`
- Records: 8
- Records with warnings: 4
- Warning codes: `{"fin_object_inequality_instead_of_value_inequality": 1, "pointwise_conclusion_instead_of_sequence_equality": 1, "substitution_proof_uses_avoided_finite_composition_helper": 1, "wrong_x_power_multiplication_side_or_shape": 1}`

| # | Warnings | Record | Generated name | Codes |
|---:|---:|---|---|---|
| 1 | 0 | `AlgebraicCombinatorics/Details/InfiniteProducts2.lean:PowerSeries.comp_prod_infinite` | `prop_fps_subs_rule_infprod` | `` |
| 2 | 0 | `AlgebraicCombinatorics/DeterminantsBasic.lean:AlgebraicCombinatorics.Det.det_swap_cols` | `det_swap_cols` | `` |
| 3 | 1 | `AlgebraicCombinatorics/FPS/Multivariate.lean:AlgebraicCombinatorics.eq_of_embedUnivInBiv_eq` | `prop_fps_mulvar_comp_y_coeff` | `pointwise_conclusion_instead_of_sequence_equality` |
| 4 | 1 | `AlgebraicCombinatorics/FPS/Substitution.lean:AlgebraicCombinatorics.fps_subs_X_right` | `fps_subs_X_right` | `substitution_proof_uses_avoided_finite_composition_helper` |
| 5 | 1 | `AlgebraicCombinatorics/FPSDefinition.lean:AlgebraicCombinatorics.FPS.coeff_mul_X_pow` | `lem_fps_xa` | `wrong_x_power_multiplication_side_or_shape` |
| 6 | 0 | `AlgebraicCombinatorics/Partitions/Basics.lean:Nat.Partition.size_eq` | `parts_sum_eq_n` | `` |
| 7 | 1 | `AlgebraicCombinatorics/Permutations/Basics.lean:AlgebraicCombinatorics.simpleTransposition_apply_of_ne` | `simpleTransposition_apply_of_ne_of_ne` | `fin_object_inequality_instead_of_value_inequality` |
| 8 | 0 | `AlgebraicCombinatorics/Permutations/Inversions1.lean:AlgebraicCombinatorics.lexLt_irrefl` | `irreflexive_lexLt` | `` |
