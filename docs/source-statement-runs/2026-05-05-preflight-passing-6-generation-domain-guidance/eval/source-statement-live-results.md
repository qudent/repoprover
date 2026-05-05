# Source-statement live eval results

- Generated at: `2026-05-05T04:02:54.654428+00:00`
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
- Actual reported cost: `$0.031387`
- Failure classes: `{}`

Success means: the prompt withheld the target Lean statement/name; the model generated a theorem/lemma; optional repairs used generated-only compiler feedback; and a grader-only copy of the gold statement was proved by `simpa using <generated theorem>`. This is still an oracle source-span benchmark, not full feed-forward segmentation.

| # | Result | Record | Generated name | Cost | Error / Lean output |
|---:|---|---|---|---:|---|
| 1 | FAIL | `AlgebraicCombinatorics/Details/Limits.lean:PowerSeries.coeffStabilizesTo_partial_sum'` | `partialSum_coeffStabilizesTo` | $0.004395 |  |
| 2 | FAIL | `AlgebraicCombinatorics/DeterminantsBasic.lean:AlgebraicCombinatorics.Det.det_swap_cols` | `det_swap_cols` | $0.004963 |  |
| 3 | FAIL | `AlgebraicCombinatorics/DeterminantsBasic.lean:AlgebraicCombinatorics.Det.det_add_smul_col` | `det_add_smul_col` | $0.005950 |  |
| 4 | FAIL | `AlgebraicCombinatorics/FPS/NotationsExamples.lean:AlgebraicCombinatorics.FPS.pascal_identity_succ` | `binom_rec` | $0.003133 |  |
| 5 | FAIL | `AlgebraicCombinatorics/FPSDefinition.lean:AlgebraicCombinatorics.FPS.X_coeff_one` | `coeff_X_fps` | $0.003045 |  |
| 6 | FAIL | `AlgebraicCombinatorics/Partitions/Basics.lean:Nat.Partition.partsCount_eq_largestPartCount` | `partsCount_eq_number_of_partitions_with_largestPart` | $0.009900 |  |
