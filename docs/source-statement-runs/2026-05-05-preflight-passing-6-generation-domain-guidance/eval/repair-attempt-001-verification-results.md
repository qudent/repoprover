# Source-statement generation verification

- Generated at: `2026-05-05T04:11:36.012384+00:00`
- Run output: `docs/source-statement-runs/2026-05-05-preflight-passing-6-generation-domain-guidance`
- Work root: `/tmp/repoprover-source-statement-verify-domain-guidance-repair1-serial`
- Workers: `1`
- Records: 6
- Successes: 2
- Success rate: 33.3%
- Failure classes: `{"missing_model_output": 4}`

| # | Result | Record | Generated name | Failure |
|---:|---|---|---|---|
| 1 | FAIL | `AlgebraicCombinatorics/Details/Limits.lean:PowerSeries.coeffStabilizesTo_partial_sum'` | `` | `missing_model_output` |
| 2 | FAIL | `AlgebraicCombinatorics/DeterminantsBasic.lean:AlgebraicCombinatorics.Det.det_swap_cols` | `` | `missing_model_output` |
| 3 | PASS | `AlgebraicCombinatorics/DeterminantsBasic.lean:AlgebraicCombinatorics.Det.det_add_smul_col` | `det_add_smul_col` | `` |
| 4 | FAIL | `AlgebraicCombinatorics/FPS/NotationsExamples.lean:AlgebraicCombinatorics.FPS.pascal_identity_succ` | `` | `missing_model_output` |
| 5 | FAIL | `AlgebraicCombinatorics/FPSDefinition.lean:AlgebraicCombinatorics.FPS.X_coeff_one` | `` | `missing_model_output` |
| 6 | PASS | `AlgebraicCombinatorics/Partitions/Basics.lean:Nat.Partition.partsCount_eq_largestPartCount` | `partsCount_eq_number_of_partitions_with_largestPart` | `` |
