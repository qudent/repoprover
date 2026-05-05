# Source-Only Context Budget Audit

- Source-only run: `docs/source-statement-runs/2026-05-05-gold64-source-only-budget`
- Context comparison: `docs/source-statement-runs/2026-05-05-gold64-source-only-budget/eval/context-mode-comparison.json`
- Records: `64`
- Estimated max generation cost: `$1.976172810`
- Hidden target-name rows: `0`
- Target-comment gap rows: `45`
- Broad source-span rows: `62`
- Multi-environment rows: `61`
- Extra-label rows: `60`
- Multi-part rows: `30`
- Rows with focused labeled environments: `64`
- Focused labeled environments extracted: `65`
- Rows with hidden-name context blocks removed: `4`
- Hidden-name context blocks removed: `4`

## Highest-Risk Rows

| # | Record | Flags | Missing Target-Comment Terms |
|---:|---|---|---|
| 1 | `AlgebraicCombinatorics/CauchyBinet.lean:AlgebraicCombinatorics.CauchyBinet.det_diagonal_submatrix_eq` | `broad, multi-env, extra-labels, multi-part, target-comment-gap, focused-label-env` | `principal, products` |
| 2 | `AlgebraicCombinatorics/DesnanotJacobi.lean:AlgebraicCombinatorics.Determinants.mul_adjugate'` | `broad, multi-env, extra-labels, target-comment-gap, focused-label-env` | `fundamental, property, multiplying, yields, determinant, including, trivial` |
| 3 | `AlgebraicCombinatorics/DesnanotJacobi.lean:AlgebraicCombinatorics.Determinants.cauchy_det` | `broad, multi-env, extra-labels, target-comment-gap, focused-label-env, hidden-name-block-filtered` | `formula, cauchy_det_of_poly, derives, version, cauchy_det_poly, strategy, textbook, cleared` |
| 4 | `AlgebraicCombinatorics/Details/InfiniteProducts2.lean:PowerSeries.coeff_zero_of_dvd` | `broad, multi-env, extra-labels, target-comment-gap, focused-label-env` | `divides, coefficients` |
| 5 | `AlgebraicCombinatorics/Details/Limits.lean:PowerSeries.tprod'_eq_of_coeffStabilizesTo_partial_prod'` | `broad, multi-env, extra-labels, target-comment-gap, focused-label-env` | `converge, equals, conclude, unique` |
| 6 | `AlgebraicCombinatorics/DeterminantsBasic.lean:AlgebraicCombinatorics.Det.det_const_matrix_eq_zero` | `broad, multi-env, extra-labels, target-comment-gap, focused-label-env` | `corollary` |
| 7 | `AlgebraicCombinatorics/DeterminantsBasic.lean:AlgebraicCombinatorics.Det.det_add_col` | `broad, multi-env, extra-labels, target-comment-gap, focused-label-env` | `adding, another, preserves, special` |
| 8 | `AlgebraicCombinatorics/DividingFPS.lean:AlgebraicCombinatorics.binomUpperNegation` | `broad, multi-env, extra-labels, target-comment-gap, focused-label-env` | `negation, binomial, coefficients, binomialring, mathlib, generalized, defined, generalizes` |
| 9 | `AlgebraicCombinatorics/DividingFPS.lean:AlgebraicCombinatorics.fps_coeff_X_pow_mul_eq_zero` | `broad, multi-env, extra-labels, focused-label-env` | `` |
| 10 | `AlgebraicCombinatorics/FPS/CommutativeRings.lean:AlgebraicCombinatorics.FPS.module_add_zero` | `broad, multi-env, multi-part, focused-label-env` | `` |
| 11 | `AlgebraicCombinatorics/FPS/CommutativeRings.lean:AlgebraicCombinatorics.FPS.module_neg_eq_neg_one_smul` | `broad, multi-env, multi-part, target-comment-gap, focused-label-env` | `modules, explicit, negation` |
| 12 | `AlgebraicCombinatorics/FPS/CommutativeRings.lean:AlgebraicCombinatorics.FPS.fraction_unit_one` | `broad, multi-env, extra-labels, multi-part, target-comment-gap, focused-label-env` | `identity, denominator` |
| 13 | `AlgebraicCombinatorics/FPS/ExpLog.lean:PowerSeries.exp_constantCoeff` | `broad, multi-env, extra-labels, multi-part, target-comment-gap, focused-label-env` | `constant` |
| 14 | `AlgebraicCombinatorics/FPS/ExpLog.lean:PowerSeries.PowerSeries₁.div_mem` | `broad, multi-env, extra-labels, multi-part, focused-label-env` | `` |
| 15 | `AlgebraicCombinatorics/FPS/ExpLog.lean:PowerSeries.loder_prod` | `broad, multi-env, extra-labels, target-comment-gap, focused-label-env, hidden-name-block-filtered` | `product, algebra` |
| 16 | `AlgebraicCombinatorics/FPS/InfiniteProducts.lean:PowerSeries.coeffFinitelyDeterminedInSum_value_unique` | `broad, multi-env, extra-labels, multi-part, target-comment-gap, focused-label-env` | `unique, determining, values` |
| 17 | `AlgebraicCombinatorics/FPS/InfiniteProducts.lean:PowerSeries.isXnApproximator_determines_coeff` | `broad, multi-env, extra-labels, focused-label-env` | `` |
| 18 | `AlgebraicCombinatorics/FPS/InfiniteProducts.lean:PowerSeries.multipliable_empty` | `broad, multi-env, extra-labels, multi-part, focused-label-env` | `` |
| 19 | `AlgebraicCombinatorics/FPS/InfiniteProducts.lean:PowerSeries.tprod_fubini_full` | `broad, multi-env, extra-labels, target-comment-gap, focused-label-env` | `computed, iterated, either, combines, directions` |
| 20 | `AlgebraicCombinatorics/FPS/InfiniteProducts1.lean:AlgebraicCombinatorics.FPS.xnEquiv_div` | `broad, multi-env, extra-labels, target-comment-gap, focused-label-env, hidden-name-block-filtered` | `coefficients, numerators, denominators, quotients` |
| 21 | `AlgebraicCombinatorics/FPS/IntegerCompositions.lean:AlgebraicCombinatorics.Composition.card_ofSizeIntoParts_pos` | `broad, multi-env, extra-labels, target-comment-gap, focused-label-env` | `number, choose, states, integer, binomial, coefficients, lean's, truncating` |
| 22 | `AlgebraicCombinatorics/FPS/LaurentSeries.lean:AlgebraicCombinatorics.FPS.Laurent.laurentPoly_add_coeff` | `broad, multi-env, extra-labels, target-comment-gap, focused-label-env` | `addition, coefficientwise` |
| 24 | `AlgebraicCombinatorics/FPS/Limits.lean:PowerSeries.coeff_div_eq_of_coeff_eq` | `broad, multi-env, extra-labels, target-comment-gap, focused-label-env` | `coefficients, denominators, quotients, direct, consequence, coefficient, quotient, depends` |
| 25 | `AlgebraicCombinatorics/FPS/Limits.lean:PowerSeries.coeffStabilizesTo_derivativeFun` | `broad, multi-env, extra-labels, target-comment-gap, focused-label-env` | `respect, derivatives` |
| 26 | `AlgebraicCombinatorics/FPS/Multivariate.lean:AlgebraicCombinatorics.sum_choose_pow_eq` | `multi-env, extra-labels, target-comment-gap, focused-label-env` | `generating, function, identity, derived, bivariate` |
| 27 | `AlgebraicCombinatorics/FPS/NotationsExamples.lean:AlgebraicCombinatorics.FPS.binom_neg_one` | `broad, multi-env, extra-labels, focused-label-env` | `` |
| 28 | `AlgebraicCombinatorics/FPS/NotationsExamples.lean:AlgebraicCombinatorics.FPS.binom_symm` | `broad, extra-labels, target-comment-gap, focused-label-env` | `natural, numbers, choose_symm` |
| 29 | `AlgebraicCombinatorics/FPS/Polynomials.lean:FPS.isPolynomial_smul` | `broad, multi-env, extra-labels, target-comment-gap, focused-label-env` | `scalar, series` |
| 30 | `AlgebraicCombinatorics/FPS/Substitution.lean:AlgebraicCombinatorics.fps_fg_coeffs_zero` | `broad, multi-env, extra-labels, focused-label-env` | `` |
| 31 | `AlgebraicCombinatorics/FPS/Substitution.lean:AlgebraicCombinatorics.fps_subs_X_left` | `broad, multi-env, extra-labels, multi-part, focused-label-env` | `` |
| 32 | `AlgebraicCombinatorics/FPS/XnEquivalence.lean:PowerSeries.xnEquiv_iff_dvd` | `broad, multi-env, extra-labels, focused-label-env` | `` |
| 33 | `AlgebraicCombinatorics/FPSDefinition.lean:AlgebraicCombinatorics.FPS.X_mul_coeff_zero` | `broad, multi-env, extra-labels, focused-label-env` | `` |
| 34 | `AlgebraicCombinatorics/FPSDefinition.lean:AlgebraicCombinatorics.FPS.X_pow_coeff` | `broad, multi-env, extra-labels, target-comment-gap, focused-label-env` | `elsewhere` |
| 35 | `AlgebraicCombinatorics/LaurentSeries.lean:AlgebraicCombinatorics.DoublyInfinitePowerSeries.eq_coeff_at_position` | `broad, multi-env, extra-labels, target-comment-gap, focused-label-env` | `equals, position, pointwise, characterization, coefficient, formalizes, representation, mentioned` |
| 36 | `AlgebraicCombinatorics/LaurentSeries.lean:AlgebraicCombinatorics.laurentPolynomial_T_neg_mul_T` | `broad, multi-env, extra-labels, focused-label-env` | `` |
| 37 | `AlgebraicCombinatorics/Partitions/Basics.lean:Nat.Partition.parts_eq_zero_of_partition_zero` | `broad, multi-env, extra-labels, multi-part, target-comment-gap, focused-label-env` | `unique` |
| 38 | `AlgebraicCombinatorics/Partitions/Basics.lean:Nat.Partition.filter_largestPart_le_eq_restricted` | `broad, multi-env, extra-labels, target-comment-gap, focused-label-env` | `equals, restricted, equivalence` |
| 39 | `AlgebraicCombinatorics/Partitions/QBinomialFormulas.lean:AlgebraicCombinatorics.QBinomialRec.qBinomial_eq_zero_of_lt` | `multi-env, extra-labels, target-comment-gap, focused-label-env` | `qbinomial_gt, hypothesis, stated` |
| 40 | `AlgebraicCombinatorics/Permutations/Basics.lean:AlgebraicCombinatorics.symmetricGroup_card` | `broad, multi-env, extra-labels, multi-part, target-comment-gap, focused-label-env` | `elements` |
| 41 | `AlgebraicCombinatorics/Permutations/Basics.lean:AlgebraicCombinatorics.symmetricGroup_iso_of_equiv` | `broad, multi-env, extra-labels, multi-part, target-comment-gap, focused-label-env` | `bijective, isomorphic, conclusion` |
