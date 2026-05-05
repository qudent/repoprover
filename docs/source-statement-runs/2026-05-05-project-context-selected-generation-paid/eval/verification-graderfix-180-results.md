# Source-statement generation verification

- Generated at: `2026-05-05T14:21:45.412348+00:00`
- Run output: `docs/source-statement-runs/2026-05-05-project-context-selected-generation-paid`
- Work root: `/tmp/repoprover-project-context-selected-verify-graderfix`
- Workers: `1`
- Records: 2
- Successes: 0
- Success rate: 0.0%
- Failure classes: `{"generated_lean_does_not_compile": 1, "grader_gold_statement_not_proved": 1}`

| # | Result | Record | Generated name | Failure |
|---:|---|---|---|---|
| 1 | FAIL | `AlgebraicCombinatorics/CauchyBinet.lean:AlgebraicCombinatorics.CauchyBinet.det_diagonal_submatrix_eq` | `det_minors_diag` | `generated_lean_does_not_compile` |
| 2 | FAIL | `AlgebraicCombinatorics/SymmetricFunctions/SchurBasics.lean:alternant_swap` | `alternant_swap_of_ne` | `grader_gold_statement_not_proved` |
