# Source-statement generation verification

- Generated at: `2026-05-05T12:06:34.308880+00:00`
- Run output: `docs/source-statement-runs/2026-05-05-gold64-easy8-source-only-generation`
- Work root: `/tmp/repoprover-gold64-easy8-verify-materialfix`
- Workers: `1`
- Records: 8
- Successes: 1
- Success rate: 12.5%
- Failure classes: `{"generated_lean_does_not_compile": 3, "grader_gold_statement_not_proved": 3, "missing_declaration": 1}`

| # | Result | Record | Generated name | Failure |
|---:|---|---|---|---|
| 1 | PASS | `AlgebraicCombinatorics/FPS/Multivariate.lean:AlgebraicCombinatorics.sum_choose_pow_eq` | `eq_fps_mulvar_exa1_res1` | `` |
| 2 | FAIL | `AlgebraicCombinatorics/LaurentSeries.lean:AlgebraicCombinatorics.laurentPolynomial_T_neg_mul_T` | `laurentPolynomial_T_isUnit_one` | `grader_gold_statement_not_proved` |
| 3 | FAIL | `AlgebraicCombinatorics/Permutations/Signs.lean:Equiv.Perm.sign_coe_eq_neg_one_pow_invCount` | `` | `missing_declaration` |
| 4 | FAIL | `AlgebraicCombinatorics/DeterminantsBasic.lean:AlgebraicCombinatorics.Det.det_add_col` | `det_colop` | `generated_lean_does_not_compile` |
| 5 | FAIL | `AlgebraicCombinatorics/FPS/XnEquivalence.lean:PowerSeries.xnEquiv_iff_dvd` | `xneq_multiple_iff` | `generated_lean_does_not_compile` |
| 6 | FAIL | `AlgebraicCombinatorics/FPS/InfiniteProducts.lean:PowerSeries.coeffFinitelyDeterminedInSum_value_unique` | `coeffFinitelyDeterminedInSum_iff` | `grader_gold_statement_not_proved` |
| 7 | FAIL | `AlgebraicCombinatorics/FPS/CommutativeRings.lean:AlgebraicCombinatorics.FPS.fraction_unit_one` | `inverse_unique` | `grader_gold_statement_not_proved` |
| 8 | FAIL | `AlgebraicCombinatorics/Partitions/QBinomialFormulas.lean:AlgebraicCombinatorics.QBinomialRec.qBinomial_eq_zero_of_lt` | `qBinomial_eq_zero_of_gt` | `generated_lean_does_not_compile` |
