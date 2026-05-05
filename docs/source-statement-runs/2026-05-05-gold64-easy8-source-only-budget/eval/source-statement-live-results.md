# Source-statement live eval results

- Generated at: `2026-05-05T11:24:27.524324+00:00`
- Model: `deepseek/deepseek-v4-pro`
- Max tokens: `32768`
- Reasoning effort: `high`
- Repair attempts: `0`
- Repair max tokens: `32768`
- Repair reasoning effort: `high`
- Context mode: `source-only`
- Preflight only: `False`
- Generation only: `False`
- Reuse project: `False`
- Concurrency: `4`
- Sample mode: `easy`
- Global cost cap: `$2.000000`
- Records attempted: 0 / selected 8
- Successes: 0
- Success rate: n/a
- Preflight successes: 0 / 0
- Generation successes: 0 / 0
- Actual reported cost: `$0.000000`
- Failure classes: `{}`

Success means: the prompt withheld the target Lean statement/name; the model generated a theorem/lemma; optional repairs used generated-only compiler feedback; and a grader-only copy of the gold statement was proved by `simpa using <generated theorem>`. This is still an oracle source-span benchmark, not full feed-forward segmentation.

| # | Result | Record | Generated name | Cost | Error / Lean output |
|---:|---|---|---|---:|---|
| 1 | BUDGET | `AlgebraicCombinatorics/FPS/Multivariate.lean:AlgebraicCombinatorics.sum_choose_pow_eq` | `` |  |  |
| 2 | BUDGET | `AlgebraicCombinatorics/LaurentSeries.lean:AlgebraicCombinatorics.laurentPolynomial_T_neg_mul_T` | `` |  |  |
| 3 | BUDGET | `AlgebraicCombinatorics/Permutations/Signs.lean:Equiv.Perm.sign_coe_eq_neg_one_pow_invCount` | `` |  |  |
| 4 | BUDGET | `AlgebraicCombinatorics/DeterminantsBasic.lean:AlgebraicCombinatorics.Det.det_add_col` | `` |  |  |
| 5 | BUDGET | `AlgebraicCombinatorics/FPS/XnEquivalence.lean:PowerSeries.xnEquiv_iff_dvd` | `` |  |  |
| 6 | BUDGET | `AlgebraicCombinatorics/FPS/InfiniteProducts.lean:PowerSeries.coeffFinitelyDeterminedInSum_value_unique` | `` |  |  |
| 7 | BUDGET | `AlgebraicCombinatorics/FPS/CommutativeRings.lean:AlgebraicCombinatorics.FPS.fraction_unit_one` | `` |  |  |
| 8 | BUDGET | `AlgebraicCombinatorics/Partitions/QBinomialFormulas.lean:AlgebraicCombinatorics.QBinomialRec.qBinomial_eq_zero_of_lt` | `` |  |  |
