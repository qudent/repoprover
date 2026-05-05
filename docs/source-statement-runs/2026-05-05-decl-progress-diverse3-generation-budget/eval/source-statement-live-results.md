# Source-statement live eval results

- Generated at: `2026-05-05T14:58:43.173608+00:00`
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
- Concurrency: `1`
- Sample mode: `corpus-spread`
- Global cost cap: `$0.120000`
- Records attempted: 0 / selected 3
- Successes: 0
- Success rate: n/a
- Preflight successes: 0 / 0
- Generation successes: 0 / 0
- Actual reported cost: `$0.000000`
- Failure classes: `{}`

Success means: the prompt withheld the target Lean statement/name; the model generated a theorem/lemma; optional repairs used generated-only compiler feedback; and a grader-only copy of the gold statement was proved by `simpa using <generated theorem>`. This is still an oracle source-span benchmark, not full feed-forward segmentation.

| # | Result | Record | Generated name | Cost | Error / Lean output |
|---:|---|---|---|---:|---|
| 1 | BUDGET | `AlgebraicCombinatorics/Details/Limits.lean:PowerSeries.tprod'_eq_of_coeffStabilizesTo_partial_prod'` | `` |  |  |
| 2 | BUDGET | `AlgebraicCombinatorics/FPS/CommutativeRings.lean:AlgebraicCombinatorics.FPS.isInverse_unique` | `` |  |  |
| 3 | BUDGET | `AlgebraicCombinatorics/FPS/LaurentSeries.lean:AlgebraicCombinatorics.FPS.Laurent.T_inv` | `` |  |  |
