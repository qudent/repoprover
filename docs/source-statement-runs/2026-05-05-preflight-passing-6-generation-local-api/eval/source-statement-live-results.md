# Source-statement live eval results

- Generated at: `2026-05-05T02:30:07.460800+00:00`
- Model: `deepseek/deepseek-v4-pro`
- Max tokens: `32768`
- Reasoning effort: `high`
- Repair attempts: `0`
- Repair max tokens: `32768`
- Repair reasoning effort: `high`
- Preflight only: `False`
- Generation only: `True`
- Reuse project: `False`
- Concurrency: `3`
- Sample mode: `corpus-spread`
- Global cost cap: `$0.250000`
- Records attempted: 6 / selected 6
- Successes: 0
- Success rate: 0.0%
- Preflight successes: 0 / 0
- Generation successes: 6 / 6
- Actual reported cost: `$0.041166`
- Failure classes: `{}`

Success means: the prompt withheld the target Lean statement/name; the model generated a theorem/lemma; optional repairs used generated-only compiler feedback; and a grader-only copy of the gold statement was proved by `simpa using <generated theorem>`. This is still an oracle source-span benchmark, not full feed-forward segmentation.

| # | Result | Record | Generated name | Cost | Error / Lean output |
|---:|---|---|---|---:|---|
| 1 | FAIL | `AlgebraicCombinatorics/Details/Limits.lean:PowerSeries.coeffStabilizesTo_partial_sum'` | `sum_lim` | $0.016047 |  |
| 2 | FAIL | `AlgebraicCombinatorics/DeterminantsBasic.lean:AlgebraicCombinatorics.Det.det_swap_cols` | `det_swap_cols` | $0.005070 |  |
| 3 | FAIL | `AlgebraicCombinatorics/DeterminantsBasic.lean:AlgebraicCombinatorics.Det.det_add_smul_col` | `det_colop` | $0.006503 |  |
| 4 | FAIL | `AlgebraicCombinatorics/FPS/NotationsExamples.lean:AlgebraicCombinatorics.FPS.pascal_identity_succ` | `binom_rec` | $0.004963 |  |
| 5 | FAIL | `AlgebraicCombinatorics/FPSDefinition.lean:AlgebraicCombinatorics.FPS.X_coeff_one` | `coeff_X_fps` | $0.003650 |  |
| 6 | FAIL | `AlgebraicCombinatorics/Partitions/Basics.lean:Nat.Partition.partsCount_eq_largestPartCount` | `partsCount_eq_card_largestPart` | $0.004932 |  |
