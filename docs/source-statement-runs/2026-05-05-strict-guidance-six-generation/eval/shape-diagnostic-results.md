# Source-statement shape diagnostic

- Generated at: `2026-05-05T08:10:00.623770+00:00`
- Run output: `docs/source-statement-runs/2026-05-05-strict-guidance-six-generation`
- Payload artifact: `openrouter-payload.json`
- Model artifact: `model-output.json`
- Records: 6
- Records with warnings: 2
- Warning codes: `{"pointwise_iteration_instead_of_group_power_statement": 1, "substitution_proof_uses_avoided_finite_composition_helper": 1}`

| # | Warnings | Record | Generated name | Codes |
|---:|---:|---|---|---|
| 1 | 0 | `AlgebraicCombinatorics/Details/Limits.lean:PowerSeries.isSummable_of_coeffStabilizesTo_partial_sum'` | `isSummable_of_partial_sum_coeffStabilizesTo` | `` |
| 2 | 0 | `AlgebraicCombinatorics/DividingFPS.lean:AlgebraicCombinatorics.fps_newtonBinomial_neg` | `fps_newton_binom` | `` |
| 3 | 1 | `AlgebraicCombinatorics/FPS/Substitution.lean:AlgebraicCombinatorics.fps_comp_coeff_finite` | `fps_comp_coeff_finite` | `substitution_proof_uses_avoided_finite_composition_helper` |
| 4 | 0 | `AlgebraicCombinatorics/Partitions/Basics.lean:Nat.Partition.parts_eq_zero_of_partition_zero` | `partition_of_zero_parts_empty` | `` |
| 5 | 1 | `AlgebraicCombinatorics/Permutations/Basics.lean:AlgebraicCombinatorics.perm_pow_succ` | `perm_pow_apply_eq_iterate` | `pointwise_iteration_instead_of_group_power_statement` |
| 6 | 0 | `AlgebraicCombinatorics/Permutations/Basics.lean:AlgebraicCombinatorics.simpleTransposition_isSwap` | `simpleTransposition_isSwap` | `` |
