# Source-statement live eval results

- Generated at: `2026-05-05T11:41:11.742873+00:00`
- Model: `deepseek/deepseek-v4-pro`
- Max tokens: `32768`
- Reasoning effort: `high`
- Repair attempts: `0`
- Repair max tokens: `32768`
- Repair reasoning effort: `high`
- Context mode: `source-only`
- Preflight only: `False`
- Generation only: `True`
- Reuse project: `False`
- Concurrency: `2`
- Sample mode: `easy`
- Global cost cap: `$0.300000`
- Records attempted: 8 / selected 8
- Successes: 0
- Success rate: 0.0%
- Preflight successes: 0 / 0
- Generation successes: 8 / 8
- Actual reported cost: `$0.071505`
- Failure classes: `{}`

Success means: the prompt withheld the target Lean statement/name; the model generated a theorem/lemma; optional repairs used generated-only compiler feedback; and a grader-only copy of the gold statement was proved by `simpa using <generated theorem>`. This is still an oracle source-span benchmark, not full feed-forward segmentation.

| # | Result | Record | Generated name | Cost | Error / Lean output |
|---:|---|---|---|---:|---|
| 1 | FAIL | `AlgebraicCombinatorics/FPS/Multivariate.lean:AlgebraicCombinatorics.sum_choose_pow_eq` | `eq_fps_mulvar_exa1_res1` | $0.004607 |  |
| 2 | FAIL | `AlgebraicCombinatorics/LaurentSeries.lean:AlgebraicCombinatorics.laurentPolynomial_T_neg_mul_T` | `laurentPolynomial_T_isUnit_one` | $0.006068 |  |
| 3 | FAIL | `AlgebraicCombinatorics/Permutations/Signs.lean:Equiv.Perm.sign_coe_eq_neg_one_pow_invCount` | `sgn` | $0.006763 |  |
| 4 | FAIL | `AlgebraicCombinatorics/DeterminantsBasic.lean:AlgebraicCombinatorics.Det.det_add_col` | `det_colop` | $0.012425 |  |
| 5 | FAIL | `AlgebraicCombinatorics/FPS/XnEquivalence.lean:PowerSeries.xnEquiv_iff_dvd` | `xneq_multiple_iff` | $0.017754 |  |
| 6 | FAIL | `AlgebraicCombinatorics/FPS/InfiniteProducts.lean:PowerSeries.coeffFinitelyDeterminedInSum_value_unique` | `coeffFinitelyDeterminedInSum_iff` | $0.011826 |  |
| 7 | FAIL | `AlgebraicCombinatorics/FPS/CommutativeRings.lean:AlgebraicCombinatorics.FPS.fraction_unit_one` | `inverse_unique` | $0.007019 |  |
| 8 | FAIL | `AlgebraicCombinatorics/Partitions/QBinomialFormulas.lean:AlgebraicCombinatorics.QBinomialRec.qBinomial_eq_zero_of_lt` | `qBinomial_eq_zero_of_gt` | $0.005045 |  |
