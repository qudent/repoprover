# Source-statement shape diagnostic

- Generated at: `2026-05-05T10:48:55.325922+00:00`
- Run output: `docs/source-statement-runs/2026-05-05-preflight-passing-11-source-only-balanced-generation`
- Payload artifact: `openrouter-payload.json`
- Model artifact: `model-output.json`
- Records: 11
- Records with warnings: 2
- Warning codes: `{"simple_transposition_equality_instead_of_isswap": 1, "substitution_proof_uses_avoided_finite_composition_helper": 1}`

| # | Warnings | Record | Generated name | Codes |
|---:|---:|---|---|---|
| 1 | 0 | `AlgebraicCombinatorics/Details/Limits.lean:PowerSeries.isSummable_of_coeffStabilizesTo_partial_sum'` | `sum_lim_conv` | `` |
| 2 | 0 | `AlgebraicCombinatorics/DeterminantsBasic.lean:AlgebraicCombinatorics.Det.det_lowerTriangular` | `det_triang` | `` |
| 3 | 0 | `AlgebraicCombinatorics/DividingFPS.lean:AlgebraicCombinatorics.fps_newtonBinomial_neg` | `fps_newton_binom` | `` |
| 4 | 0 | `AlgebraicCombinatorics/FPS/InfiniteProducts.lean:PowerSeries.coeffFinitelyDeterminedInProd_of_finite` | `CoeffFinitelyDeterminedInSum` | `` |
| 5 | 0 | `AlgebraicCombinatorics/FPS/InfiniteProducts.lean:PowerSeries.exists_xn_approximator` | `exists_isXnApproximator_of_multipliable` | `` |
| 6 | 0 | `AlgebraicCombinatorics/FPS/NotationsExamples.lean:AlgebraicCombinatorics.FPS.binom_symm` | `binom_sym` | `` |
| 7 | 1 | `AlgebraicCombinatorics/FPS/Substitution.lean:AlgebraicCombinatorics.fps_comp_coeff_finite` | `fps_subst_eq_tsum` | `substitution_proof_uses_avoided_finite_composition_helper` |
| 8 | 0 | `AlgebraicCombinatorics/FPSDefinition.lean:AlgebraicCombinatorics.FPS.X_mul_eq_shift` | `X_mul_eq` | `` |
| 9 | 0 | `AlgebraicCombinatorics/Partitions/Basics.lean:Nat.Partition.parts_eq_zero_of_partition_zero` | `card_partitions_of_5` | `` |
| 10 | 0 | `AlgebraicCombinatorics/Permutations/Basics.lean:AlgebraicCombinatorics.perm_pow_succ` | `card_perm` | `` |
| 11 | 1 | `AlgebraicCombinatorics/Permutations/Basics.lean:AlgebraicCombinatorics.simpleTransposition_isSwap` | `simpleTransposition_eq_transposition` | `simple_transposition_equality_instead_of_isswap` |
