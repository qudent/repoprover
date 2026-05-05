# Source-statement generation verification

- Generated at: `2026-05-05T14:43:30.848874+00:00`
- Run output: `docs/source-statement-runs/2026-05-05-project-context-diverse3-generation-paid`
- Work root: `/tmp/repoprover-project-context-diverse3-verify`
- Workers: `1`
- Records: 3
- Successes: 1
- Success rate: 33.3%
- Failure classes: `{"generated_lean_does_not_compile": 1, "grader_gold_statement_not_proved": 1}`

| # | Result | Record | Generated name | Failure |
|---:|---|---|---|---|
| 1 | FAIL | `AlgebraicCombinatorics/Details/Limits.lean:PowerSeries.tprod'_eq_of_coeffStabilizesTo_partial_prod'` | `product_lim_conv` | `grader_gold_statement_not_proved` |
| 2 | PASS | `AlgebraicCombinatorics/FPS/CommutativeRings.lean:AlgebraicCombinatorics.FPS.isInverse_unique` | `thm_commring_inverse_uni` | `` |
| 3 | FAIL | `AlgebraicCombinatorics/FPS/LaurentSeries.lean:AlgebraicCombinatorics.FPS.Laurent.T_inv` | `laupol_ring` | `generated_lean_does_not_compile` |
