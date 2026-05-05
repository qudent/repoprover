# Source-statement generation verification

- Generated at: `2026-05-05T03:20:49.846389+00:00`
- Run output: `docs/source-statement-runs/2026-05-05-preflight-passing-6-generation-target-comment`
- Work root: `/tmp/repoprover-source-statement-verify-target-comment-repair1-serial`
- Workers: `1`
- Records: 6
- Successes: 1
- Success rate: 16.7%
- Failure classes: `{"forbidden_placeholder": 1, "generated_lean_does_not_compile": 1, "missing_model_output": 3}`

| # | Result | Record | Generated name | Failure |
|---:|---|---|---|---|
| 1 | FAIL | `AlgebraicCombinatorics/Details/Limits.lean:PowerSeries.coeffStabilizesTo_partial_sum'` | `sum_lim_eq_tsum` | `forbidden_placeholder` |
| 2 | FAIL | `AlgebraicCombinatorics/DeterminantsBasic.lean:AlgebraicCombinatorics.Det.det_swap_cols` | `` | `missing_model_output` |
| 3 | FAIL | `AlgebraicCombinatorics/DeterminantsBasic.lean:AlgebraicCombinatorics.Det.det_add_smul_col` | `` | `missing_model_output` |
| 4 | FAIL | `AlgebraicCombinatorics/FPS/NotationsExamples.lean:AlgebraicCombinatorics.FPS.pascal_identity_succ` | `` | `missing_model_output` |
| 5 | PASS | `AlgebraicCombinatorics/FPSDefinition.lean:AlgebraicCombinatorics.FPS.X_coeff_one` | `coeff_X_eq` | `` |
| 6 | FAIL | `AlgebraicCombinatorics/Partitions/Basics.lean:Nat.Partition.partsCount_eq_largestPartCount` | `partsCount_eq_card_largestPart_eq` | `generated_lean_does_not_compile` |
