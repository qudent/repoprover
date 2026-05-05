# Source-statement live eval results

- Generated at: `2026-05-05T15:03:09.235419+00:00`
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
- Concurrency: `1`
- Sample mode: `corpus-spread`
- Global cost cap: `$0.120000`
- Records attempted: 3 / selected 3
- Successes: 0
- Success rate: 0.0%
- Preflight successes: 0 / 0
- Generation successes: 3 / 3
- Actual reported cost: `$0.019770`
- Failure classes: `{}`

Success means: the prompt withheld the target Lean statement/name; the model generated a theorem/lemma; optional repairs used generated-only compiler feedback; and a grader-only copy of the gold statement was proved by `simpa using <generated theorem>`. This is still an oracle source-span benchmark, not full feed-forward segmentation.

| # | Result | Record | Generated name | Cost | Error / Lean output |
|---:|---|---|---|---:|---|
| 1 | FAIL | `AlgebraicCombinatorics/Details/Limits.lean:PowerSeries.tprod'_eq_of_coeffStabilizesTo_partial_prod'` | `tprod'_eq_of_coeffStabilizesTo_partial_prod'` | $0.009574 |  |
| 2 | FAIL | `AlgebraicCombinatorics/FPS/CommutativeRings.lean:AlgebraicCombinatorics.FPS.isInverse_unique` | `isInverse_unique` | $0.003024 |  |
| 3 | FAIL | `AlgebraicCombinatorics/FPS/LaurentSeries.lean:AlgebraicCombinatorics.FPS.Laurent.T_inv` | `laurentPoly_unity_and_invertible` | $0.007173 |  |
