# Source-statement live eval results

- Generated at: `2026-05-05T06:28:24.520968+00:00`
- Model: `deepseek/deepseek-v4-pro`
- Max tokens: `32768`
- Reasoning effort: `high`
- Repair attempts: `0`
- Repair max tokens: `32768`
- Repair reasoning effort: `high`
- Preflight only: `True`
- Generation only: `False`
- Reuse project: `True`
- Concurrency: `1`
- Sample mode: `corpus-spread`
- Global cost cap: `$2.000000`
- Records attempted: 0 / selected 36
- Successes: 0
- Success rate: n/a
- Preflight successes: 11 / 36
- Generation successes: 0 / 0
- Actual reported cost: `$0.000000`
- Failure classes: `{"verifier_preflight_error": 2, "verifier_preflight_failed": 23}`

Success means: the prompt withheld the target Lean statement/name; the model generated a theorem/lemma; optional repairs used generated-only compiler feedback; and a grader-only copy of the gold statement was proved by `simpa using <generated theorem>`. This is still an oracle source-span benchmark, not full feed-forward segmentation.

| # | Result | Record | Generated name | Cost | Error / Lean output |
|---:|---|---|---|---:|---|
| 1 | FAIL | `AlgebraicCombinatorics/CauchyBinet.lean:AlgebraicCombinatorics.CauchyBinet.det_diagonal_submatrix_eq` | `` |  |  |
| 2 | FAIL | `AlgebraicCombinatorics/DesnanotJacobi.lean:AlgebraicCombinatorics.Determinants.desnanot_jacobi_general` | `` |  |  |
| 3 | PASS | `AlgebraicCombinatorics/Details/Limits.lean:PowerSeries.isSummable_of_coeffStabilizesTo_partial_sum'` | `` |  |  |
| 4 | PASS | `AlgebraicCombinatorics/DeterminantsBasic.lean:AlgebraicCombinatorics.Det.det_lowerTriangular` | `` |  |  |
| 5 | PASS | `AlgebraicCombinatorics/DividingFPS.lean:AlgebraicCombinatorics.fps_newtonBinomial_neg` | `` |  |  |
| 6 | FAIL | `AlgebraicCombinatorics/FPS/CommutativeRings.lean:AlgebraicCombinatorics.FPS.module_add_zero` | `` |  |  |
| 7 | FAIL | `AlgebraicCombinatorics/FPS/CommutativeRings.lean:AlgebraicCombinatorics.FPS.fraction_one` | `` |  |  |
| 8 | FAIL | `AlgebraicCombinatorics/FPS/ExpLog.lean:PowerSeries.PowerSeries₀.zero_mem` | `` |  |  |
| 9 | PASS | `AlgebraicCombinatorics/FPS/InfiniteProducts.lean:PowerSeries.coeffFinitelyDeterminedInProd_of_finite` | `` |  |  |
| 10 | PASS | `AlgebraicCombinatorics/FPS/InfiniteProducts.lean:PowerSeries.exists_xn_approximator` | `` |  |  |
| 11 | FAIL | `AlgebraicCombinatorics/FPS/InfiniteProducts.lean:PowerSeries.tprod_fubini_full` | `` |  |  |
| 12 | FAIL | `AlgebraicCombinatorics/FPS/InfiniteProducts2.lean:coeff_mul_tprod_one_add_eq_coeff` | `` |  |  |
| 13 | FAIL | `AlgebraicCombinatorics/FPS/LaurentSeries.lean:AlgebraicCombinatorics.FPS.Laurent.T_neg_one_mul_T` | `` |  |  |
| 14 | FAIL | `AlgebraicCombinatorics/FPS/Limits.lean:PowerSeries.coeffStabilizesTo_mul` | `` |  |  |
| 15 | FAIL | `AlgebraicCombinatorics/FPS/NonIntegerPowers.lean:AlgebraicCombinatorics.FPS.constantCoeff_fpsPow` | `` |  |  |
| 16 | PASS | `AlgebraicCombinatorics/FPS/NotationsExamples.lean:AlgebraicCombinatorics.FPS.binom_symm` | `` |  |  |
| 17 | PASS | `AlgebraicCombinatorics/FPS/Substitution.lean:AlgebraicCombinatorics.fps_comp_coeff_finite` | `` |  |  |
| 18 | FAIL | `AlgebraicCombinatorics/FPS/WeightedSets.lean:WeightedSet.weightGenFun_eq_of_isomorphic` | `` |  |  |
| 19 | PASS | `AlgebraicCombinatorics/FPSDefinition.lean:AlgebraicCombinatorics.FPS.X_mul_eq_shift` | `` |  |  |
| 20 | FAIL | `AlgebraicCombinatorics/LaurentSeries.lean:AlgebraicCombinatorics.DoublyInfinitePowerSeries.isLaurentSeries_ofLaurentSeries` | `` |  |  |
| 21 | PASS | `AlgebraicCombinatorics/Partitions/Basics.lean:Nat.Partition.parts_eq_zero_of_partition_zero` | `` |  |  |
| 22 | FAIL | `AlgebraicCombinatorics/Partitions/Basics.lean:Nat.Partition.partsCount_sum_eq_partsLeqCount` | `` |  |  |
| 23 | PASS | `AlgebraicCombinatorics/Permutations/Basics.lean:AlgebraicCombinatorics.perm_pow_succ` | `` |  |  |
| 24 | PASS | `AlgebraicCombinatorics/Permutations/Basics.lean:AlgebraicCombinatorics.simpleTransposition_isSwap` | `` |  |  |
| 25 | FAIL | `AlgebraicCombinatorics/Permutations/CycleDecomposition.lean:AlgebraicCombinatorics.CycleDecomposition.sign_eq_neg_one_pow_card_sub_numCycles` | `` |  |  |
| 26 | FAIL | `AlgebraicCombinatorics/Permutations/Signs.lean:Equiv.Perm.sign_coe_eq_neg_one_pow_invCount` | `` |  |  |
| 27 | FAIL | `AlgebraicCombinatorics/SymmetricFunctions/Definitions.lean:AlgebraicCombinatorics.SymmetricPolynomials.permAction_eq_rename` | `` |  |  |
| 28 | FAIL | `AlgebraicCombinatorics/SymmetricFunctions/Definitions.lean:AlgebraicCombinatorics.SymmetricPolynomials.permAutomorphism_symm` | `` |  |  |
| 29 | FAIL | `AlgebraicCombinatorics/SymmetricFunctions/Definitions.lean:AlgebraicCombinatorics.SymmetricPolynomials.S_neg_mem` | `` |  |  |
| 30 | FAIL | `AlgebraicCombinatorics/SymmetricFunctions/Definitions.lean:AlgebraicCombinatorics.SymmetricPolynomials.Monomial.degree_zero` | `` |  |  |
| 31 | FAIL | `AlgebraicCombinatorics/SymmetricFunctions/Definitions.lean:AlgebraicCombinatorics.SymmetricPolynomials.Monomial.degree_ofFinset` | `` |  |  |
| 32 | FAIL | `AlgebraicCombinatorics/SymmetricFunctions/Definitions.lean:AlgebraicCombinatorics.SymmetricPolynomials.eZ_isSymmetric` | `` |  |  |
| 33 | FAIL | `AlgebraicCombinatorics/SymmetricFunctions/Definitions.lean:AlgebraicCombinatorics.SymmetricPolynomials.newtonGirard_psum` | `` |  |  |
| 34 | FAIL | `AlgebraicCombinatorics/SymmetricFunctions/LittlewoodRichardson.lean:AlgebraicCombinatorics.alternant_eq_zero_of_repeated` | `` |  |  |
| 35 | FAIL | `AlgebraicCombinatorics/SymmetricFunctions/PieriJacobiTrudi.lean:SymmetricFunctions.skewSchur_isSymmetric_jacobiTrudi` | `` |  | TimeoutExpired: Command '['uv', 'run', 'lake', 'build', 'AlgebraicCombinatorics.Determinants.LGV2', 'AlgebraicCombinatorics.SymmetricFunctions.OmegaInvolution', 'AlgebraicCombinatorics.SymmetricFunctions.NPartition', 'Al |
| 36 | FAIL | `AlgebraicCombinatorics/SymmetricFunctions/SchurBasics.lean:alternant_swap` | `` |  | TimeoutExpired: Command '['uv', 'run', 'lake', 'build', 'AlgebraicCombinatorics.SymmetricFunctions.LittlewoodRichardson', 'AlgebraicCombinatorics.SymmetricFunctions.NPartition', 'AlgebraicCombinatorics.Permutations.Basic |
