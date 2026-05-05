# Source-Statement Hard-Guidance Results

Date: 2026-05-05

## Change

After the larger 8-record validation exposed failures in FPS
infinite-products/substitution, multivariate coefficient projection, and exact
statement-shape matching, the prompt gained hard-example guidance for:

- formal power series infinite-product substitution without topological `tprod`
  APIs;
- multivariate FPS coefficient projection through `embedUnivInBiv`;
- substitution by `X` using the local `HasSubst.X'`/`coeff_subst'` proof shape;
- right-vs-left multiplication by powers of `X`;
- simple transposition fixed-point statement shape.

## API-Free Budget Check

Output: `/tmp/repoprover-source-statement-hard-guidance-budget-8`

- Selected records: 8
- Estimated max generation cost: `$0.240149145`
- Paid calls: 0
- Prompt inspection confirmed the new guidance appeared on the intended hard
  rows.
- Prompt inspection found no `theorem target`,
  `__repoprover_source_statement_check`, API key, bearer token, or OpenRouter
  secret marker.

## Paid Run

Artifacts:
`docs/source-statement-runs/2026-05-05-preflight-passing-8-generation-hard-guidance`

Generation-only run:

- Paid calls: 8
- Parsed generations: 8/8
- Actual reported OpenRouter cost: `$0.047175431`
- Serial verification: 2/8 successes
- Failure classes:
  `generated_lean_does_not_compile=3`,
  `grader_gold_statement_not_proved=3`

Repair attempt 1:

- Targeted generated-only compile failures: records 1, 2, and 4
- Paid calls: 3
- Actual reported OpenRouter cost: `$0.029584437`
- Verified repair successes: 1/3 (`AlgebraicCombinatorics.Det.det_swap_cols`)

Total hard-guidance generation plus repair cost: `$0.076759868`.

## Cumulative Result

| # | Record | First pass | Repair | Best result | Remaining issue |
|---:|---|---|---|---|---|
| 1 | `PowerSeries.comp_prod_infinite` | FAIL | FAIL | FAIL | Statement shape moved toward the local approximator API, but generated proof still had Lean equality-direction mistakes. |
| 2 | `AlgebraicCombinatorics.Det.det_swap_cols` | FAIL | PASS | PASS | Repair fixed a stale/guessed matrix transpose helper. |
| 3 | `AlgebraicCombinatorics.eq_of_embedUnivInBiv_eq` | FAIL | n/a | FAIL | Generated theorem proved `∀ k, f k = g k`; this compiles but does not match the hidden theorem shape `f = g`. |
| 4 | `AlgebraicCombinatorics.fps_subs_X_right` | FAIL | FAIL | FAIL | Generated proof still mishandles the off-diagonal `finsum_eq_single` side condition. |
| 5 | `AlgebraicCombinatorics.FPS.coeff_mul_X_pow` | FAIL | n/a | FAIL | Guidance did not prevent fallback to the special `X * f` equality form instead of the right-multiplication `f * X^k` coefficient theorem. |
| 6 | `Nat.Partition.size_eq` | PASS | n/a | PASS |  |
| 7 | `AlgebraicCombinatorics.simpleTransposition_apply_of_ne` | FAIL | n/a | FAIL | Generated theorem compiled but used Fin-object inequality assumptions instead of the local value-inequality statement. |
| 8 | `AlgebraicCombinatorics.lexLt_irrefl` | PASS | n/a | PASS |  |

Final cumulative result for this hard-guidance 8-record rerun: 3/8 verified
successes, the same total as the previous larger-slice run.

## Interpretation

The new guidance changed failure modes but did not improve the larger-slice
success rate. This is useful because it separates two problems:

- compile-only issues can often be repaired cheaply from generated-only Lean
  errors;
- semantic/shape mismatches need a stronger pre-generation context contract
  because repair prompts intentionally do not see the hidden grader statement.

The next no/low-cost iteration should add a semantic-shape diagnostic layer for
source-statement generation outputs, using only visible source comments and
prompt context. The layer should flag likely mismatches such as:

- generated conclusion is `∀ k, f k = g k` when the source target is an equality
  of sequences;
- generated statement uses `X * f` when the source focus says `f * X^k`;
- generated assumptions use constructed `Fin` object inequalities when the
  local target comments and context suggest value inequalities.

That diagnostic can then drive targeted context retrieval or a pre-repair
statement-shape rewrite without exposing the hidden gold Lean statement.
