# Source-statement generation verification

- Generated at: `2026-05-05T03:43:54.094352+00:00`
- Run output: `docs/source-statement-runs/2026-05-05-preflight-passing-6-generation-import-label-guidance`
- Work root: `/tmp/repoprover-source-statement-verify-import-label-guidance-serial-rerun`
- Workers: `1`
- Records: 6
- Successes: 3
- Success rate: 50.0%
- Failure classes: `{"generated_lean_does_not_compile": 3}`

| # | Result | Record | Generated name | Failure |
|---:|---|---|---|---|
| 1 | PASS | `AlgebraicCombinatorics/Details/Limits.lean:PowerSeries.coeffStabilizesTo_partial_sum'` | `sum_lim` | `` |
| 2 | PASS | `AlgebraicCombinatorics/DeterminantsBasic.lean:AlgebraicCombinatorics.Det.det_swap_cols` | `det_swap_cols` | `` |
| 3 | FAIL | `AlgebraicCombinatorics/DeterminantsBasic.lean:AlgebraicCombinatorics.Det.det_add_smul_col` | `det_add_smul_col` | `generated_lean_does_not_compile` |
| 4 | PASS | `AlgebraicCombinatorics/FPS/NotationsExamples.lean:AlgebraicCombinatorics.FPS.pascal_identity_succ` | `binom_rec` | `` |
| 5 | FAIL | `AlgebraicCombinatorics/FPSDefinition.lean:AlgebraicCombinatorics.FPS.X_coeff_one` | `coeff_X_eq` | `generated_lean_does_not_compile` |
| 6 | FAIL | `AlgebraicCombinatorics/Partitions/Basics.lean:Nat.Partition.partsCount_eq_largestPartCount` | `partsCount_eq_largestPart_count` | `generated_lean_does_not_compile` |
