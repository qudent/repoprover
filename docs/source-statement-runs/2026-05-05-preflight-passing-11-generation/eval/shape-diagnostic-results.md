# Source-statement shape diagnostic

- Generated at: `2026-05-05T06:48:31.883697+00:00`
- Run output: `docs/source-statement-runs/2026-05-05-preflight-passing-11-generation`
- Payload artifact: `openrouter-payload.json`
- Model artifact: `model-output.json`
- Records: 11
- Records with warnings: 2
- Warning codes: `{"substitution_proof_uses_avoided_finite_composition_helper": 1, "wrong_x_power_multiplication_side_or_shape": 1}`

| # | Warnings | Record | Generated name | Codes |
|---:|---:|---|---|---|
| 1 | 0 | `AlgebraicCombinatorics/Details/Limits.lean:PowerSeries.isSummable_of_coeffStabilizesTo_partial_sum'` | `summable_and_tsum'_eq_of_coeffStabilizesTo_partial_sum` | `` |
| 2 | 0 | `AlgebraicCombinatorics/DeterminantsBasic.lean:AlgebraicCombinatorics.Det.det_lowerTriangular` | `det_lowerTriangular` | `` |
| 3 | 0 | `AlgebraicCombinatorics/DividingFPS.lean:AlgebraicCombinatorics.fps_newtonBinomial_neg` | `fps_newton_binom` | `` |
| 4 | 0 | `AlgebraicCombinatorics/FPS/InfiniteProducts.lean:PowerSeries.coeffFinitelyDeterminedInProd_of_finite` | `coeffFinitelyDeterminedInProd_of_finite` | `` |
| 5 | 0 | `AlgebraicCombinatorics/FPS/InfiniteProducts.lean:PowerSeries.exists_xn_approximator` | `exists_isXnApproximator_of_multipliable` | `` |
| 6 | 0 | `AlgebraicCombinatorics/FPS/NotationsExamples.lean:AlgebraicCombinatorics.FPS.binom_symm` | `binom_symm` | `` |
| 7 | 1 | `AlgebraicCombinatorics/FPS/Substitution.lean:AlgebraicCombinatorics.fps_comp_coeff_finite` | `fps_comp_coeff_eq_finset_sum` | `substitution_proof_uses_avoided_finite_composition_helper` |
| 8 | 1 | `AlgebraicCombinatorics/FPSDefinition.lean:AlgebraicCombinatorics.FPS.X_mul_eq_shift` | `lem_fps_xa` | `wrong_x_power_multiplication_side_or_shape` |
| 9 | 0 | `AlgebraicCombinatorics/Partitions/Basics.lean:Nat.Partition.parts_eq_zero_of_partition_zero` | `size_eq_zero_iff_eq_empty` | `` |
| 10 | 0 | `AlgebraicCombinatorics/Permutations/Basics.lean:AlgebraicCombinatorics.perm_pow_succ` | `pow_eq_iterate` | `` |
| 11 | 0 | `AlgebraicCombinatorics/Permutations/Basics.lean:AlgebraicCombinatorics.simpleTransposition_isSwap` | `simpleTransposition_eq_transposition` | `` |
