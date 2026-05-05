# Source-statement generation verification

- Generated at: `2026-05-05T01:40:14.107345+00:00`
- Run output: `docs/source-statement-runs/2026-05-05-preflight-passing-6-generation`
- Work root: `/tmp/repoprover-source-statement-verify-preflight-passing-6-serial`
- Workers: `1`
- Records: 6
- Successes: 0
- Success rate: 0.0%
- Failure classes: `{"generated_lean_does_not_compile": 5, "grader_gold_statement_not_proved": 1}`

| # | Result | Record | Generated name | Failure |
|---:|---|---|---|---|
| 1 | FAIL | `AlgebraicCombinatorics/Details/Limits.lean:PowerSeries.coeffStabilizesTo_partial_sum'` | `sum_lim` | `generated_lean_does_not_compile` |
| 2 | FAIL | `AlgebraicCombinatorics/DeterminantsBasic.lean:AlgebraicCombinatorics.Det.det_swap_cols` | `det_colop` | `generated_lean_does_not_compile` |
| 3 | FAIL | `AlgebraicCombinatorics/DeterminantsBasic.lean:AlgebraicCombinatorics.Det.det_add_smul_col` | `det_colop` | `generated_lean_does_not_compile` |
| 4 | FAIL | `AlgebraicCombinatorics/FPS/NotationsExamples.lean:AlgebraicCombinatorics.FPS.pascal_identity_succ` | `binom_rec` | `grader_gold_statement_not_proved` |
| 5 | FAIL | `AlgebraicCombinatorics/FPSDefinition.lean:AlgebraicCombinatorics.FPS.X_coeff_one` | `x_coeff_spec` | `generated_lean_does_not_compile` |
| 6 | FAIL | `AlgebraicCombinatorics/Partitions/Basics.lean:Nat.Partition.partsCount_eq_largestPartCount` | `partsCount_eq_card_filter_largestPart` | `generated_lean_does_not_compile` |
