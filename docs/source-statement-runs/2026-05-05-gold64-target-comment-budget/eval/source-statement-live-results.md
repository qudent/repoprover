# Source-statement live eval results

- Generated at: `2026-05-05T11:13:39.778143+00:00`
- Model: `deepseek/deepseek-v4-pro`
- Max tokens: `32768`
- Reasoning effort: `high`
- Repair attempts: `0`
- Repair max tokens: `32768`
- Repair reasoning effort: `high`
- Context mode: `target-comment`
- Preflight only: `False`
- Generation only: `False`
- Reuse project: `False`
- Concurrency: `4`
- Sample mode: `corpus-spread`
- Global cost cap: `$2.000000`
- Records attempted: 0 / selected 64
- Successes: 0
- Success rate: n/a
- Preflight successes: 0 / 0
- Generation successes: 0 / 0
- Actual reported cost: `$0.000000`
- Failure classes: `{}`

Success means: the prompt withheld the target Lean statement/name; the model generated a theorem/lemma; optional repairs used generated-only compiler feedback; and a grader-only copy of the gold statement was proved by `simpa using <generated theorem>`. This is still an oracle source-span benchmark, not full feed-forward segmentation.

| # | Result | Record | Generated name | Cost | Error / Lean output |
|---:|---|---|---|---:|---|
| 1 | BUDGET | `AlgebraicCombinatorics/CauchyBinet.lean:AlgebraicCombinatorics.CauchyBinet.det_diagonal_submatrix_eq` | `` |  |  |
| 2 | BUDGET | `AlgebraicCombinatorics/DesnanotJacobi.lean:AlgebraicCombinatorics.Determinants.mul_adjugate'` | `` |  |  |
| 3 | BUDGET | `AlgebraicCombinatorics/DesnanotJacobi.lean:AlgebraicCombinatorics.Determinants.cauchy_det` | `` |  |  |
| 4 | BUDGET | `AlgebraicCombinatorics/Details/InfiniteProducts2.lean:PowerSeries.coeff_zero_of_dvd` | `` |  |  |
| 5 | BUDGET | `AlgebraicCombinatorics/Details/Limits.lean:PowerSeries.tprod'_eq_of_coeffStabilizesTo_partial_prod'` | `` |  |  |
| 6 | BUDGET | `AlgebraicCombinatorics/DeterminantsBasic.lean:AlgebraicCombinatorics.Det.det_const_matrix_eq_zero` | `` |  |  |
| 7 | BUDGET | `AlgebraicCombinatorics/DeterminantsBasic.lean:AlgebraicCombinatorics.Det.det_add_col` | `` |  |  |
| 8 | BUDGET | `AlgebraicCombinatorics/DividingFPS.lean:AlgebraicCombinatorics.binomUpperNegation` | `` |  |  |
| 9 | BUDGET | `AlgebraicCombinatorics/DividingFPS.lean:AlgebraicCombinatorics.fps_coeff_X_pow_mul_eq_zero` | `` |  |  |
| 10 | BUDGET | `AlgebraicCombinatorics/FPS/CommutativeRings.lean:AlgebraicCombinatorics.FPS.module_add_zero` | `` |  |  |
| 11 | BUDGET | `AlgebraicCombinatorics/FPS/CommutativeRings.lean:AlgebraicCombinatorics.FPS.module_neg_eq_neg_one_smul` | `` |  |  |
| 12 | BUDGET | `AlgebraicCombinatorics/FPS/CommutativeRings.lean:AlgebraicCombinatorics.FPS.fraction_unit_one` | `` |  |  |
| 13 | BUDGET | `AlgebraicCombinatorics/FPS/ExpLog.lean:PowerSeries.exp_constantCoeff` | `` |  |  |
| 14 | BUDGET | `AlgebraicCombinatorics/FPS/ExpLog.lean:PowerSeries.PowerSeries₁.div_mem` | `` |  |  |
| 15 | BUDGET | `AlgebraicCombinatorics/FPS/ExpLog.lean:PowerSeries.loder_prod` | `` |  |  |
| 16 | BUDGET | `AlgebraicCombinatorics/FPS/InfiniteProducts.lean:PowerSeries.coeffFinitelyDeterminedInSum_value_unique` | `` |  |  |
| 17 | BUDGET | `AlgebraicCombinatorics/FPS/InfiniteProducts.lean:PowerSeries.isXnApproximator_determines_coeff` | `` |  |  |
| 18 | BUDGET | `AlgebraicCombinatorics/FPS/InfiniteProducts.lean:PowerSeries.multipliable_empty` | `` |  |  |
| 19 | BUDGET | `AlgebraicCombinatorics/FPS/InfiniteProducts.lean:PowerSeries.tprod_fubini_full` | `` |  |  |
| 20 | BUDGET | `AlgebraicCombinatorics/FPS/InfiniteProducts1.lean:AlgebraicCombinatorics.FPS.xnEquiv_div` | `` |  |  |
| 21 | BUDGET | `AlgebraicCombinatorics/FPS/IntegerCompositions.lean:AlgebraicCombinatorics.Composition.card_ofSizeIntoParts_pos` | `` |  |  |
| 22 | BUDGET | `AlgebraicCombinatorics/FPS/LaurentSeries.lean:AlgebraicCombinatorics.FPS.Laurent.laurentPoly_add_coeff` | `` |  |  |
| 23 | BUDGET | `AlgebraicCombinatorics/FPS/LaurentSeries.lean:AlgebraicCombinatorics.FPS.Laurent.order_mul_ge` | `` |  |  |
| 24 | BUDGET | `AlgebraicCombinatorics/FPS/Limits.lean:PowerSeries.coeff_div_eq_of_coeff_eq` | `` |  |  |
| 25 | BUDGET | `AlgebraicCombinatorics/FPS/Limits.lean:PowerSeries.coeffStabilizesTo_derivativeFun` | `` |  |  |
| 26 | BUDGET | `AlgebraicCombinatorics/FPS/Multivariate.lean:AlgebraicCombinatorics.sum_choose_pow_eq` | `` |  |  |
| 27 | BUDGET | `AlgebraicCombinatorics/FPS/NotationsExamples.lean:AlgebraicCombinatorics.FPS.binom_neg_one` | `` |  |  |
| 28 | BUDGET | `AlgebraicCombinatorics/FPS/NotationsExamples.lean:AlgebraicCombinatorics.FPS.binom_symm` | `` |  |  |
| 29 | BUDGET | `AlgebraicCombinatorics/FPS/Polynomials.lean:FPS.isPolynomial_smul` | `` |  |  |
| 30 | BUDGET | `AlgebraicCombinatorics/FPS/Substitution.lean:AlgebraicCombinatorics.fps_fg_coeffs_zero` | `` |  |  |
| 31 | BUDGET | `AlgebraicCombinatorics/FPS/Substitution.lean:AlgebraicCombinatorics.fps_subs_X_left` | `` |  |  |
| 32 | BUDGET | `AlgebraicCombinatorics/FPS/XnEquivalence.lean:PowerSeries.xnEquiv_iff_dvd` | `` |  |  |
| 33 | BUDGET | `AlgebraicCombinatorics/FPSDefinition.lean:AlgebraicCombinatorics.FPS.X_mul_coeff_zero` | `` |  |  |
| 34 | BUDGET | `AlgebraicCombinatorics/FPSDefinition.lean:AlgebraicCombinatorics.FPS.X_pow_coeff` | `` |  |  |
| 35 | BUDGET | `AlgebraicCombinatorics/LaurentSeries.lean:AlgebraicCombinatorics.DoublyInfinitePowerSeries.eq_coeff_at_position` | `` |  |  |
| 36 | BUDGET | `AlgebraicCombinatorics/LaurentSeries.lean:AlgebraicCombinatorics.laurentPolynomial_T_neg_mul_T` | `` |  |  |
| 37 | BUDGET | `AlgebraicCombinatorics/Partitions/Basics.lean:Nat.Partition.parts_eq_zero_of_partition_zero` | `` |  |  |
| 38 | BUDGET | `AlgebraicCombinatorics/Partitions/Basics.lean:Nat.Partition.filter_largestPart_le_eq_restricted` | `` |  |  |
| 39 | BUDGET | `AlgebraicCombinatorics/Partitions/QBinomialFormulas.lean:AlgebraicCombinatorics.QBinomialRec.qBinomial_eq_zero_of_lt` | `` |  |  |
| 40 | BUDGET | `AlgebraicCombinatorics/Permutations/Basics.lean:AlgebraicCombinatorics.symmetricGroup_card` | `` |  |  |
| 41 | BUDGET | `AlgebraicCombinatorics/Permutations/Basics.lean:AlgebraicCombinatorics.symmetricGroup_iso_of_equiv` | `` |  |  |
| 42 | BUDGET | `AlgebraicCombinatorics/Permutations/Basics.lean:AlgebraicCombinatorics.simpleTransposition_apply_succ` | `` |  |  |
| 43 | BUDGET | `AlgebraicCombinatorics/Permutations/Basics.lean:AlgebraicCombinatorics.simpleTransposition_inv` | `` |  |  |
| 44 | BUDGET | `AlgebraicCombinatorics/Permutations/Basics.lean:AlgebraicCombinatorics.isInvolution_of_disjoint_transpositions` | `` |  |  |
| 45 | BUDGET | `AlgebraicCombinatorics/Permutations/Inversions1.lean:AlgebraicCombinatorics.lexLt_asymm` | `` |  |  |
| 46 | BUDGET | `AlgebraicCombinatorics/Permutations/Signs.lean:Equiv.Perm.sign_coe_eq_neg_one_pow_invCount` | `` |  |  |
| 47 | BUDGET | `AlgebraicCombinatorics/SignedCounting/AlternatingSums.lean:AlgebraicCombinatorics.SignedCounting.isPrimitiveRoot_iff_pow_eq_one_and_pow_ne_one` | `` |  |  |
| 48 | BUDGET | `AlgebraicCombinatorics/SymmetricFunctions/Definitions.lean:AlgebraicCombinatorics.SymmetricPolynomials.isSymm_iff_permAction` | `` |  |  |
| 49 | BUDGET | `AlgebraicCombinatorics/SymmetricFunctions/Definitions.lean:AlgebraicCombinatorics.SymmetricPolynomials.permAutomorphism_one` | `` |  |  |
| 50 | BUDGET | `AlgebraicCombinatorics/SymmetricFunctions/Definitions.lean:AlgebraicCombinatorics.SymmetricPolynomials.S_one_mem` | `` |  |  |
| 51 | BUDGET | `AlgebraicCombinatorics/SymmetricFunctions/Definitions.lean:AlgebraicCombinatorics.SymmetricPolynomials.isSymm_mul` | `` |  |  |
| 52 | BUDGET | `AlgebraicCombinatorics/SymmetricFunctions/Definitions.lean:AlgebraicCombinatorics.SymmetricPolynomials.S_pow_mem` | `` |  |  |
| 53 | BUDGET | `AlgebraicCombinatorics/SymmetricFunctions/Definitions.lean:AlgebraicCombinatorics.SymmetricPolynomials.Monomial.toPoly_zero` | `` |  |  |
| 54 | BUDGET | `AlgebraicCombinatorics/SymmetricFunctions/Definitions.lean:AlgebraicCombinatorics.SymmetricPolynomials.Monomial.isPrimal_single` | `` |  |  |
| 55 | BUDGET | `AlgebraicCombinatorics/SymmetricFunctions/Definitions.lean:AlgebraicCombinatorics.SymmetricPolynomials.Monomial.degree_ofFinset` | `` |  |  |
| 56 | BUDGET | `AlgebraicCombinatorics/SymmetricFunctions/Definitions.lean:AlgebraicCombinatorics.SymmetricPolynomials.e_zero` | `` |  |  |
| 57 | BUDGET | `AlgebraicCombinatorics/SymmetricFunctions/Definitions.lean:AlgebraicCombinatorics.SymmetricPolynomials.hZ_of_nonneg` | `` |  |  |
| 58 | BUDGET | `AlgebraicCombinatorics/SymmetricFunctions/Definitions.lean:AlgebraicCombinatorics.SymmetricPolynomials.h_eq_sum_prod_sym` | `` |  |  |
| 59 | BUDGET | `AlgebraicCombinatorics/SymmetricFunctions/Definitions.lean:AlgebraicCombinatorics.SymmetricPolynomials.isAntisymm_zero` | `` |  |  |
| 60 | BUDGET | `AlgebraicCombinatorics/SymmetricFunctions/LittlewoodRichardson.lean:AlgebraicCombinatorics.subTuple_apply'` | `` |  |  |
| 61 | BUDGET | `AlgebraicCombinatorics/SymmetricFunctions/MonomialSymmetric.lean:AlgebraicCombinatorics.SymmetricFunctions.monomialSymm_isSymmetric` | `` |  |  |
| 62 | BUDGET | `AlgebraicCombinatorics/SymmetricFunctions/PieriJacobiTrudi.lean:SymmetricFunctions.SkewPartition.horizontalStrip_iff_entries` | `` |  |  |
| 63 | BUDGET | `AlgebraicCombinatorics/SymmetricFunctions/SchurBasics.lean:SkewSSYT.col_strict_of_lt` | `` |  |  |
| 64 | BUDGET | `AlgebraicCombinatorics/SymmetricFunctions/SchurBasics.lean:alternant_swap` | `` |  |  |
