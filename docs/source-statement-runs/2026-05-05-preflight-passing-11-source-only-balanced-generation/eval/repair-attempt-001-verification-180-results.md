# Source-statement generation verification

- Generated at: `2026-05-05T10:54:00.083094+00:00`
- Run output: `docs/source-statement-runs/2026-05-05-preflight-passing-11-source-only-balanced-generation`
- Work root: `/tmp/repoprover-source-only-balanced-shape-repair-verify`
- Workers: `1`
- Records: 2
- Successes: 0
- Success rate: 0.0%
- Failure classes: `{"generated_lean_does_not_compile": 1, "grader_gold_statement_not_proved": 1}`

| # | Result | Record | Generated name | Failure |
|---:|---|---|---|---|
| 7 | FAIL | `AlgebraicCombinatorics/FPS/Substitution.lean:AlgebraicCombinatorics.fps_comp_coeff_finite` | `fps_subst_eq_mk_finsum` | `grader_gold_statement_not_proved` |
| 11 | FAIL | `AlgebraicCombinatorics/Permutations/Basics.lean:AlgebraicCombinatorics.simpleTransposition_isSwap` | `simpleTransposition_isSwap` | `generated_lean_does_not_compile` |
