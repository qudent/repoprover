# Source-statement generation verification

- Generated at: `2026-05-05T03:13:34.186507+00:00`
- Run output: `docs/source-statement-runs/2026-05-05-preflight-passing-6-generation-target-comment`
- Work root: `/tmp/repoprover-source-statement-verify-target-comment-serial`
- Workers: `1`
- Records: 6
- Successes: 3
- Success rate: 50.0%
- Failure classes: `{"generated_lean_does_not_compile": 3}`

| # | Result | Record | Generated name | Failure |
|---:|---|---|---|---|
| 1 | FAIL | `AlgebraicCombinatorics/Details/Limits.lean:PowerSeries.coeffStabilizesTo_partial_sum'` | `sum_lim_eq_tsum` | `generated_lean_does_not_compile` |
| 2 | PASS | `AlgebraicCombinatorics/DeterminantsBasic.lean:AlgebraicCombinatorics.Det.det_swap_cols` | `det_swap_cols` | `` |
| 3 | PASS | `AlgebraicCombinatorics/DeterminantsBasic.lean:AlgebraicCombinatorics.Det.det_add_smul_col` | `det_add_smul_col` | `` |
| 4 | PASS | `AlgebraicCombinatorics/FPS/NotationsExamples.lean:AlgebraicCombinatorics.FPS.pascal_identity_succ` | `binom_succ_succ` | `` |
| 5 | FAIL | `AlgebraicCombinatorics/FPSDefinition.lean:AlgebraicCombinatorics.FPS.X_coeff_one` | `coeff_X_eq` | `generated_lean_does_not_compile` |
| 6 | FAIL | `AlgebraicCombinatorics/Partitions/Basics.lean:Nat.Partition.partsCount_eq_largestPartCount` | `partsCount_eq_card_largestPart_eq` | `generated_lean_does_not_compile` |
