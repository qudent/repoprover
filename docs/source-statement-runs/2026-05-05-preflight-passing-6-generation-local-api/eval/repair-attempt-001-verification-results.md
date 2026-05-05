# Source-statement generation verification

- Generated at: `2026-05-05T02:47:32.043931+00:00`
- Run output: `docs/source-statement-runs/2026-05-05-preflight-passing-6-generation-local-api`
- Work root: `/tmp/repoprover-source-statement-verify-local-api-repair1-serial`
- Workers: `1`
- Records: 6
- Successes: 2
- Success rate: 33.3%
- Failure classes: `{"generated_lean_does_not_compile": 2, "grader_gold_statement_not_proved": 1, "missing_model_output": 1}`

| # | Result | Record | Generated name | Failure |
|---:|---|---|---|---|
| 1 | FAIL | `AlgebraicCombinatorics/Details/Limits.lean:PowerSeries.coeffStabilizesTo_partial_sum'` | `sum_lim` | `generated_lean_does_not_compile` |
| 2 | PASS | `AlgebraicCombinatorics/DeterminantsBasic.lean:AlgebraicCombinatorics.Det.det_swap_cols` | `det_swap_cols` | `` |
| 3 | FAIL | `AlgebraicCombinatorics/DeterminantsBasic.lean:AlgebraicCombinatorics.Det.det_add_smul_col` | `det_colop` | `grader_gold_statement_not_proved` |
| 4 | FAIL | `AlgebraicCombinatorics/FPS/NotationsExamples.lean:AlgebraicCombinatorics.FPS.pascal_identity_succ` | `` | `missing_model_output` |
| 5 | PASS | `AlgebraicCombinatorics/FPSDefinition.lean:AlgebraicCombinatorics.FPS.X_coeff_one` | `coeff_X_fps` | `` |
| 6 | FAIL | `AlgebraicCombinatorics/Partitions/Basics.lean:Nat.Partition.partsCount_eq_largestPartCount` | `partsCount_eq_card_largestPart` | `generated_lean_does_not_compile` |
