# Source-statement generation verification

- Generated at: `2026-05-05T03:48:12.881071+00:00`
- Run output: `docs/source-statement-runs/2026-05-05-preflight-passing-6-generation-import-label-guidance`
- Work root: `/tmp/repoprover-source-statement-verify-import-label-guidance-repair1-serial`
- Workers: `1`
- Records: 6
- Successes: 1
- Success rate: 16.7%
- Failure classes: `{"generated_lean_does_not_compile": 2, "missing_model_output": 3}`

| # | Result | Record | Generated name | Failure |
|---:|---|---|---|---|
| 1 | FAIL | `AlgebraicCombinatorics/Details/Limits.lean:PowerSeries.coeffStabilizesTo_partial_sum'` | `` | `missing_model_output` |
| 2 | FAIL | `AlgebraicCombinatorics/DeterminantsBasic.lean:AlgebraicCombinatorics.Det.det_swap_cols` | `` | `missing_model_output` |
| 3 | PASS | `AlgebraicCombinatorics/DeterminantsBasic.lean:AlgebraicCombinatorics.Det.det_add_smul_col` | `det_add_smul_col` | `` |
| 4 | FAIL | `AlgebraicCombinatorics/FPS/NotationsExamples.lean:AlgebraicCombinatorics.FPS.pascal_identity_succ` | `` | `missing_model_output` |
| 5 | FAIL | `AlgebraicCombinatorics/FPSDefinition.lean:AlgebraicCombinatorics.FPS.X_coeff_one` | `coeff_X_eq` | `generated_lean_does_not_compile` |
| 6 | FAIL | `AlgebraicCombinatorics/Partitions/Basics.lean:Nat.Partition.partsCount_eq_largestPartCount` | `partsCount_eq_largestPart_count` | `generated_lean_does_not_compile` |
