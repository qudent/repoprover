# Source-statement generation verification

- Generated at: `2026-05-05T02:55:27.227374+00:00`
- Run output: `docs/source-statement-runs/2026-05-05-preflight-passing-6-generation-local-api`
- Work root: `/tmp/repoprover-source-statement-verify-local-api-repair2-serial`
- Workers: `1`
- Records: 6
- Successes: 0
- Success rate: 0.0%
- Failure classes: `{"generated_lean_does_not_compile": 1, "grader_gold_statement_not_proved": 1, "missing_model_output": 4}`

| # | Result | Record | Generated name | Failure |
|---:|---|---|---|---|
| 1 | FAIL | `AlgebraicCombinatorics/Details/Limits.lean:PowerSeries.coeffStabilizesTo_partial_sum'` | `sum_lim` | `grader_gold_statement_not_proved` |
| 2 | FAIL | `AlgebraicCombinatorics/DeterminantsBasic.lean:AlgebraicCombinatorics.Det.det_swap_cols` | `` | `missing_model_output` |
| 3 | FAIL | `AlgebraicCombinatorics/DeterminantsBasic.lean:AlgebraicCombinatorics.Det.det_add_smul_col` | `` | `missing_model_output` |
| 4 | FAIL | `AlgebraicCombinatorics/FPS/NotationsExamples.lean:AlgebraicCombinatorics.FPS.pascal_identity_succ` | `` | `missing_model_output` |
| 5 | FAIL | `AlgebraicCombinatorics/FPSDefinition.lean:AlgebraicCombinatorics.FPS.X_coeff_one` | `` | `missing_model_output` |
| 6 | FAIL | `AlgebraicCombinatorics/Partitions/Basics.lean:Nat.Partition.partsCount_eq_largestPartCount` | `partsCount_eq_card_largestPart` | `generated_lean_does_not_compile` |
