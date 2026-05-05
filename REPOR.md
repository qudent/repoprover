# RepoProver Work Report - Last ~9 Hours

Report time: 2026-05-05 10:20 UTC.

## Goal Being Advanced

Validate a cheap, iterative autoformalization loop for the Algebraic Combinatorics gold-standard dataset under the remaining OpenRouter research budget. The larger goal is a reproducible system that can autoformalize book-scale material far below a one-shot human/agent price, using mostly cheap model tokens, honest context selection, Lean feedback, and occasional stronger repair.

## Main Pipeline Changes

- Decoupled paid generation from Lean checking: OpenRouter calls write recoverable run artifacts first, and Lean verification consumes those artifacts later with reusable project work roots.
- Confirmed serial verification is not the bottleneck at the current scale. Provider generation and exact statement/proof quality dominate.
- Added and exercised stricter source-statement guidance for hard FPS, partition, and permutation rows.
- Added shape diagnostics that inspect only visible prompt context plus generated Lean, so statement-shape mistakes can be targeted without exposing gold statements.
- Added repair-queue cost reservation before request launch, fixing the earlier overspend mode where concurrent calls could exceed the cap before actual cost was known.
- Improved generated-application candidate parsing for nested binders and Unicode Lean identifiers, which fixed hidden-grader verification for a valid permutation repair.
- Added `--context-mode source-only` to remove target Lean doc comments, target-derived labels, hidden-name guidance triggers, and imported source-label API retrieval from model-facing prompts.
- Added TeX-derived `tex_source_focus` fields from visible source only: labels, refs, theorem-like environments, part markers, keyword cues, excerpts, and broad-span risk flags.
- Added context-mode comparison artifacts to quantify the gap between target-comment debugging prompts and realistic source-only prompts.
- Added TeX environment-balance span risks and bounded line-range expansion so source-only prompts can include missing theorem/proposition bodies.

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

5. Row 2/3 follow-up:
   - Added repair-domain guidance for:
     - `fps_onePlusX_pow_neg'` implicit type-argument misuse and integer-power instance failures.
     - finite `finsum_eq_sum_of_support_subset` support-subset proof shape.
   - Fixed a false shape-diagnostic warning on row 3: `fps_comp_coeff` is expected for `fps_comp_coeff_finite`.
   - Focused tests passed: `58 passed`.
   - Repair attempt 3 for rows 2 and 3 finished with 2/2 parsed outputs, 2 paid calls, and `$0.012440043` actual cost under a `$0.08` cap.
   - Row 2 generated a direct `fps_onePlusX_pow_neg' n` proof shape.
   - Row 3 generated a revised `finsum_eq_sum_of_support_subset` proof that treats `hd` as support membership.
   - Serial Lean verification passed both attempt-3 repairs.

6. Realistic-context pivot:
   - Added source-only prompt mode because the 6/6 strict result still used target-comment/oracle-ish context.
   - Generated zero-cost source-only budget checkpoints for the strict 6 and broader 11 slices.
   - Context comparison found 0 hidden target-name hits, but target-comment focus terms were absent from source-only spans in 5/6 strict rows and 7/11 broader rows.
   - Added TeX-derived focus extraction to recover generic source cues without reading target Lean comments or names.
   - Ran an 11-record source-only generation-only validation with DeepSeek V4 Pro: 11/11 generated for `$0.081084638`; initial Lean verification passed 1/11.
   - Ran compile-failure repair attempt 1 over the broader source-only slice: 7/8 repair outputs for `$0.058516809`, with 3/7 passing hidden-grader verification.
   - Retried the row-1 transient provider failure: one output for `$0.013631334`, but it still failed generated-only compilation.
   - Found row 11’s source-only prompt cut off at `\begin{proposition}` before the proposition body; added environment-balance span-risk flags plus bounded TeX span expansion and regenerated the 11-record budget audit.
   - Ran a fresh 11-record paid source-only generation with balanced spans: `$0.126677307`, 10/11 usable outputs, 1/11 verified.
   - Added visible `IsSwap` shape diagnostics and missing-helper repair guidance, then ran two shape-warning repairs for `$0.014849247`; no additional row passed.

## Current Best Results

Validated strict hard-slice result:

- 6/6 cumulatively verified.
- Cost: `$0.21569744` for strict generation plus recorded repairs.
- Passing rows: 1, 4, 5, 6 from earlier generation/repair stages; rows 2 and 3 from repair attempt 3.
- Limitation: this used target-comment context, so it is debugging evidence, not realistic feed-forward evidence.

Realistic source-only result so far:

- 11/11 generated under source-only context.
- Generation plus repair cost: `$0.153232781`.
- Hidden target names absent from prompt payloads.
- Lean verification: 1/11 passed, 8 generated declarations did not compile, and 2 compiled but did not prove the withheld gold statement.
- Cumulative after compile-failure repair: 4/11 pass (`X_mul_eq_shift`, `fps_onePlusX_pow_int`, `exists_isXnApproximator_of_multipliable`, `binom_sym`).
- The two compile-clean semantic misses were `det_triangular` answering a broader disjunction instead of lower-triangular only, and `simpleTransposition_sq_eq_one` answering order-two instead of `Perm.IsSwap`.
- `fps_comp_coeff_finite` compiled after repair but still proved summability, not the finite coefficient formula; the source-only span is under-focused for that target.
- `simpleTransposition_isSwap` exposed a source-span bug: the prompt stopped before a proposition body. The regenerated budget prompt expands that row from lines 256-278 to 255-290.
- The balanced-span rerun did not improve aggregate pass rate: it still verified 1/11 before repair, and shape-warning repairs did not add a pass.

## Files And Evidence

- Main run: `docs/source-statement-runs/2026-05-05-strict-guidance-six-generation/`
- Main strict report: `docs/source-statement-strict-guidance-six-generation-report.md`
- Budget checkpoint: `docs/source-statement-strict-guidance-six-budget-report.md`
- Targeted-guidance failure report: `docs/source-statement-targeted-guidance-six-generation-report.md`
- Shape diagnostic script: `scripts/diagnose_source_statement_shape.py`
- Repair queue: `scripts/repair_source_statement_generation.py`
- Source prompt/repair builder: `scripts/run_source_statement_live_eval.py`
- Realistic context report: `docs/source-statement-realistic-context-mode-report.md`
- Source-only 11-record generation run: `docs/source-statement-runs/2026-05-05-preflight-passing-11-source-only-generation/`
- Source-only 11-record verification: `docs/source-statement-runs/2026-05-05-preflight-passing-11-source-only-generation/eval/verification-180-results.md`
- Source-only repair verification: `docs/source-statement-runs/2026-05-05-preflight-passing-11-source-only-generation/eval/repair-attempt-001-verification-180-results.md`
- Regenerated source-only budget audit: `docs/source-statement-runs/2026-05-05-preflight-passing-11-source-only-budget/`
- Focused test files:
  - `tests/test_source_statement_generation_artifacts.py`
  - `tests/test_source_statement_live_eval.py`

## Practical Conclusions

- The architecture is now good enough for cheap iteration: provider calls, verification, diagnostics, and repairs are decoupled and file-backed.
- The earlier 6-row loop did spend too much attention on one small hard slice; it produced useful infrastructure and failure taxonomy, but it should not be treated as scale evidence.
- The prompt improvements split into two classes: generic infrastructure/guidance that can transfer, and target-comment guidance that is now isolated behind `target-comment` mode for diagnostics only.
- The next useful work is context selection, not more row-local repair: remaining failures include under-focused source spans and semantic theorem-family misses that compiler-only repair cannot honestly fix.
- A visible-context shape diagnostic initially flagged the passing `X_mul_eq_shift` row because it read broad prompt guidance as source evidence; that diagnostic has been tightened so warnings are anchored in source/focus text.
