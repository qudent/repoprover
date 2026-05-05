# Source-statement generation verification

- Generated at: `2026-05-05T13:20:30.831028+00:00`
- Run output: `docs/source-statement-runs/2026-05-05-context-selected-generation-paid`
- Work root: `/tmp/repoprover-context-selected-generation-verify`
- Workers: `1`
- Records: 2
- Successes: 0
- Success rate: 0.0%
- Failure classes: `{"generated_lean_does_not_compile": 1, "missing_model_output": 1}`

| # | Result | Record | Generated name | Failure |
|---:|---|---|---|---|
| 1 | FAIL | `AlgebraicCombinatorics/CauchyBinet.lean:AlgebraicCombinatorics.CauchyBinet.det_diagonal_submatrix_eq` | `` | `missing_model_output` |
| 2 | FAIL | `AlgebraicCombinatorics/SymmetricFunctions/SchurBasics.lean:alternant_swap` | `alternant_properties` | `generated_lean_does_not_compile` |
