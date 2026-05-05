# RepoProver Work Report - Last ~7 Hours

Report time: 2026-05-05 08:35 UTC.

## Goal Being Advanced

Validate a cheap, iterative autoformalization loop for the Algebraic Combinatorics gold-standard dataset under the remaining OpenRouter research budget. The current honest task is target-statement-withheld source-to-Lean generation: prompts may use source text, prefix Lean context, local examples, and generated-only compiler errors, but not the hidden target Lean statement or declaration name.

## Main Pipeline Changes

- Decoupled paid generation from Lean checking: OpenRouter calls write recoverable run artifacts first, and Lean verification consumes those artifacts later with reusable project work roots.
- Confirmed serial verification is not the bottleneck at the current scale. Provider generation and exact statement/proof quality dominate.
- Added and exercised stricter source-statement guidance for hard FPS, partition, and permutation rows.
- Added shape diagnostics that inspect only visible prompt context plus generated Lean, so statement-shape mistakes can be targeted without exposing gold statements.
- Added repair-queue cost reservation before request launch, fixing the earlier overspend mode where concurrent calls could exceed the cap before actual cost was known.
- Improved generated-application candidate parsing for nested binders and Unicode Lean identifiers, which fixed hidden-grader verification for a valid permutation repair.

## Experiment Timeline

1. Targeted six-row guidance over the remaining hard rows from the 11-record source-statement run:
   - Budget-only prompt check: `$0.00`, hidden target names absent.
   - Paid generation: 6/6 parsed for `$0.03896991`.
   - Serial verification: 0/6 verified.

2. Strict six-row guidance:
   - Budget-only prompt check: `$0.00`, with specific lessons for FPS limits, finite `finsum`, partition zero, permutation powers, and `IsSwap`.
   - Paid generation: `$0.0308386`, 2/6 verified first pass.

3. Strict repair attempt 1:
   - Targeted three compile failures.
   - Paid cost: `$0.166295128`.
   - Recovered row 6 (`IsSwap`), bringing cumulative strict slice to 3/6.
   - Exposed repair cost-cap bug; fixed it with tests.

4. Shape diagnostics and row 5 repair:
   - Added `pointwise_iteration_instead_of_group_power_statement`.
   - Paid row 5 shape repair: `$0.006123669`.
   - Fixed verifier binder parsing; row 5 then passed generated-only and hidden-grader checks.
   - Cumulative strict hard slice reached 4/6 for `$0.203257397`.

5. Current row 2/3 follow-up:
   - Added repair-domain guidance for:
     - `fps_onePlusX_pow_neg'` implicit type-argument misuse and integer-power instance failures.
     - finite `finsum_eq_sum_of_support_subset` support-subset proof shape.
   - Fixed a false shape-diagnostic warning on row 3: `fps_comp_coeff` is expected for `fps_comp_coeff_finite`.
   - Focused tests passed: `58 passed`.
   - Repair attempt 3 for rows 2 and 3 finished with 2/2 parsed outputs, 2 paid calls, and `$0.012440043` actual cost under a `$0.08` cap.
   - Row 2 generated a direct `fps_onePlusX_pow_neg' n` proof shape.
   - Row 3 generated a revised `finsum_eq_sum_of_support_subset` proof that treats `hd` as support membership.

## Current Best Result

Best validated strict hard-slice result before Lean-checking attempt 3:

- 4/6 verified.
- Cost: `$0.203257397` for strict generation plus recorded repairs.
- Passing rows: 1, 4, 5, 6.
- Open rows: 2 negative-binomial inverse-power formula, 3 finite substitution coefficient formula.

Attempt 3 has parsed repair outputs for both open rows, but they still need Lean verification before counting them as successes.

## Files And Evidence

- Main run: `docs/source-statement-runs/2026-05-05-strict-guidance-six-generation/`
- Main strict report: `docs/source-statement-strict-guidance-six-generation-report.md`
- Budget checkpoint: `docs/source-statement-strict-guidance-six-budget-report.md`
- Targeted-guidance failure report: `docs/source-statement-targeted-guidance-six-generation-report.md`
- Shape diagnostic script: `scripts/diagnose_source_statement_shape.py`
- Repair queue: `scripts/repair_source_statement_generation.py`
- Source prompt/repair builder: `scripts/run_source_statement_live_eval.py`
- Focused test files:
  - `tests/test_source_statement_generation_artifacts.py`
  - `tests/test_source_statement_live_eval.py`

## Practical Conclusions

- The architecture is now good enough for cheap iteration: provider calls, verification, diagnostics, and repairs are decoupled and file-backed.
- The prompt still does not mostly succeed on larger slices, so dependency-graph trust scoring should still wait.
- The next useful work is not a larger paid run; it is committing the raw attempt-3 artifacts, verifying them, and, if needed, adding more zero-cost diagnostics for the two remaining exact proof-shape failures.
