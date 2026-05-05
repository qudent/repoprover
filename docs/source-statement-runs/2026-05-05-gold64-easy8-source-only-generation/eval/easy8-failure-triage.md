# Gold64 Easy-8 Failure Triage

Date: 2026-05-05.

## Corrected Verification

The initial `verification-180` run reported `1/8` pass, `6` generated-only
compile failures, and `1` hidden-grader semantic miss. That overstated compile
failures because materialization closed named sections with a bare `end`.

After fixing named section closes, `verification-sectionfix-180` reports:

- successes: `1/8`
- generated-only compile failures: `3`
- hidden-grader semantic misses after generated-only compile success: `3`
- missing theorem/lemma declaration: `1`

## Rows

| # | Record | Generated name | Corrected class | Triage |
|---:|---|---|---|---|
| 1 | `AlgebraicCombinatorics.sum_choose_pow_eq` | `eq_fps_mulvar_exa1_res1` | pass | Correct theorem family; direct existing lemma was enough. |
| 2 | `AlgebraicCombinatorics.laurentPolynomial_T_neg_mul_T` | `laurentPolynomial_T_isUnit_one` | grader semantic miss | Generated a true invertibility theorem for `T 1`, but the gold target is the multiplicative inverse identity for `T n * T (-n)`. Context focus was too broad inside a theorem about algebra structure and invertibility. |
| 3 | `Equiv.Perm.sign_coe_eq_neg_one_pow_invCount` | none | missing declaration | Model returned `def sgn`, not a theorem/lemma. Future runs now reject this at generation-contract time. |
| 4 | `AlgebraicCombinatorics.Det.det_add_col` | `det_colop` | compile failure | Statement bundled column swap/add/smul conclusions; proof fails on transpose/update-column extensionality goals. This is repairable, but also shows multi-conclusion source spans invite over-bundling. |
| 5 | `PowerSeries.xnEquiv_iff_dvd` | `xneq_multiple_iff` | compile failure | Theorem family is plausible, but proof invents brittle coefficient rewrites for `coeff_sub`, `coeff_mul`, and `coeff_X_pow`. Repair would need API-grounded coefficient guidance. |
| 6 | `PowerSeries.coeffFinitelyDeterminedInSum_value_unique` | `coeffFinitelyDeterminedInSum_iff` | grader semantic miss | Generated an iff/definition unpacking theorem; gold target expects uniqueness/value equality for two determining finite subsets. This is a theorem-family miss from definition-focused context. |
| 7 | `AlgebraicCombinatorics.FPS.fraction_unit_one` | `inverse_unique` | grader semantic miss | Generated a generic inverse uniqueness lemma; gold target is a fraction/inverse identity involving unity. Source span has multiple definition parts and weak specific focus. |
| 8 | `AlgebraicCombinatorics.QBinomialRec.qBinomial_eq_zero_of_lt` | `qBinomial_eq_zero_of_gt` | compile failure | Good theorem-family direction, but generated against the wrong `qBinomial` API/signature and collided with an existing declaration. Needs local API grounding or same-namespace collision avoidance. |

## Takeaways

- The section-close bug was a verifier/materialization issue and is fixed in
  `context_close_commands`.
- The easy-8 run still validates the main concern: broad source spans often
  produce the wrong theorem family even when focused labeled environments are
  present.
- Next paid work should not simply scale generation. Better next low-cost work:
  add statement-family diagnostics for definition-vs-theorem focus, conjunction
  over-bundling, and generated declarations that collide with local names.
