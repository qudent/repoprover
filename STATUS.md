# RepoProver - Status
## Overall Direction
Build a cheap, reproducible source-to-Lean autoformalization pipeline for
Algebraic Combinatorics. The production unit is one LaTeX theorem/environment as
a planning work item, decomposed into Lean declarations with selected
source/project/local/Mathlib context and post-hoc semantic verification.

-------

## Current State
The repo has pivoted from declaration-level rows to theorem-level LaTeX
statement rows. Current datasets are `docs/latex-statement-units.jsonl` and
`docs/latex-statement-gold-candidates.jsonl`; the retired declaration-level
artifacts are preserved at `checkpoint/before-per-latex-statement-dataset`.

## Active Goals
- [ ] Use LaTeX statement units as the main benchmark/planning surface.
- [ ] Keep paid selector/generation outputs recoverable before verification.
- [ ] Select source text, previous source statements, previous project
  declarations, local file/import/style context, and Mathlib APIs separately.
- [ ] Move from declaration-level pass/fail toward theorem-level semantic
  coverage with inner-loop Lean checks.

## TODO Plan
- [x] Generate theorem-level source units and gold-candidate rows.
- [x] Add Lean-tooling hydration for selector-requested Mathlib names.
- [x] Add theorem-level generation, generated-only verification, exact-name
  gold comparison, and semantic coverage grading.
- [x] Infer verification imports/opens from selected prior project context.
- [x] Add compact local file-context candidates and cap same-file predecessor
  context before batch-size growth.
- [ ] Reclassify old strict-grader mismatches into `compile_failure`,
  `missing_context`, `wrong_math`, `shape_mismatch_against_oracle`, or
  `useful_alternative_formalization`.
- [x] Run one theorem-level batch-size-2 v4 selector/generation smoke.
- [x] Attach source-scan Mathlib fallback candidates when selector guesses
  hydrate as unknown constants.
- [x] Add same-file local predecessor declaration context with target omitted
  and explicit benchmark-honesty provenance.
- [x] Add theorem-level LLM/Lean repair runner using failed output, verifier
  errors, fallback Mathlib candidates, and local predecessor context.
- [x] Add autonomous context-repair selection for checked proof ingredients
  before relying on agent-selected repair packs.
- [ ] Generalize the autonomous repair-context loop beyond one symmetric unit
  and reduce noisy fallback-context candidates.

## Blockers
- The old declaration-level verifier can reject useful source-theorem progress
  when generated declarations do not match one hidden Lean row.
- Previous-project context has been the strongest signal, but it must stay
  target-blind. Current selector payloads use full source-unit prior context and
  hide selected-unit aligned target declarations.
- Local file context matters: determinant transpose only became a clean pass
  after the generator saw safe prior local context and emitted explicit binders.
- Batch-2 v4 exposed the next blocker: selector can understand the math but
  misremember a Mathlib lemma name (`MvPolynomial.esymm_eq_zero_of_lt`), and the
  generator may still violate the `cannot_prove` empty-output contract.
- The new fallback search finds the relevant `MvPolynomial.esymm` declarations
  for that unknown-name guess, but not a direct vanishing theorem; the symmetric
  unit likely needs local proof-pattern context as well.
- Paid v5/v5b symmetric probes show the model still over-trusts an unavailable
  Mathlib lemma even when hydration marks it as failed; the verifier now flags
  both nonempty body and nonempty names for invalid `cannot_prove` outputs.
- Autonomous repair-context selection now reaches `1/1` compile and `1/1`
  semantic coverage on the symmetric `e_n = 0` unit, but it needed four
  context-selection rounds and several repair calls. The next blocker is making
  that loop cheaper, less noisy, and reliable across a broader theorem batch.
- Full Lean dependency extraction is feasible but heavy on this 8 GB machine;
  reuse `docs/lean-elaborated-direct-deps.jsonl` unless a rerun is needed.

## Recent Results
- Dataset scale: 462 LaTeX source units, 114 gold-candidate units, 414 aligned
  Lean declarations; median 2 aligned declarations per gold unit, p90 8, max 29.
- Lean dependency summary over 114 units: median 44 direct Mathlib constants and
  median 5 direct project constants per unit.
- Inverse uniqueness v3:
  `docs/latex-statement-context-runs/2026-05-05-inverse-unique-prior-project-v3-paid/`
  plus generation run of the same name. Selector cost `$0.00038332`, generation
  cost `$0.0004417`, generated-only compile `1/1`, exact-name overlap `0/1`,
  semantic coverage `1/1`.
- Determinant transpose v4:
  `docs/latex-statement-context-runs/2026-05-05-det-transp-localctx-v4-paid/`
  and
  `docs/latex-statement-generation-runs/2026-05-05-det-transp-localctx-v4-paid/`.
  Selector payload shrank from 26,956 to 19,984 bytes; selector cost
  `$0.00071918`; generation cost `$0.00076272`; generated-only compile `1/1`;
  exact-name overlap `0/1`; semantic coverage `1/1`.
- Batch-2 v4 smoke:
  `docs/latex-statement-context-runs/2026-05-05-batch2-selected-localctx-v4-paid/`
  selected determinant multiplicativity and symmetric `e_n = 0`; selector cost
  `$0.00164794`, valid JSON, `0` reasoning tokens. Hydration checked
  `Matrix.det_mul` but rejected unknown `MvPolynomial.esymm_eq_zero_of_lt`.
  Generation cost `$0.00200256`; verification compiled `1/2`; semantic coverage
  was `1/2` with `coverage_status_counts = {all_aligned_gold_proved: 1,
  generated_not_compiled: 1}`.
- Hydration fallback rerun:
  `docs/latex-statement-context-runs/2026-05-05-batch2-selected-localctx-v4-paid/batch-001/mathlib-lean-hydrated-context.json`
  now attaches ranked `MvPolynomial.esymm`-area candidates for the bad selector
  guess, including `MvPolynomial.esymm_eq_sum_subtype` and
  `MvPolynomial.esymm_zero`.
- Symmetric local-predecessor budget payload:
  `docs/latex-statement-context-runs/2026-05-05-symmetric-local-predecessor-v5-budget/`
  is budget-only/no paid call and exposes same-file prior helpers such as
  `e_eq_sum_prod_subsets` while omitting the selected target theorem.
- Symmetric paid v5:
  `docs/latex-statement-context-runs/2026-05-05-symmetric-local-predecessor-v5-paid/`
  cost `$0.00114492`; generation v5 cost `$0.0019204`, v5b cost `$0.00138432`.
  Both generated outputs failed `0/1`; v5 used the unknown Mathlib theorem, and
  v5b marked `cannot_prove_from_visible_context` but still emitted code/names.
- Symmetric repair rounds:
  `docs/latex-statement-generation-runs/2026-05-05-symmetric-local-predecessor-v5b-repair1-paid/`
  produced a contract-clean `cannot_prove`. Repair3 with
  `checked-proof-ingredients.json` cost `$0.00170492`, generated Lean that
  compiled `1/1`, and semantic coverage proved the aligned gold theorem `1/1`.
- Autonomous symmetric repair-context loop:
  `docs/latex-statement-context-runs/2026-05-05-symmetric-repair-context-v1-paid/`
  through `v4-paid/` selected target-hidden context, Lean-hydrated exact and
  fallback Mathlib signatures, and drove repair4-8. Repair8 compiled `1/1` and
  semantic coverage proved the aligned gold theorem `1/1`; additional loop
  cost was `$0.02180284`. Key selected ingredients were
  `e_eq_sum_prod_subsets`, `Finset.powersetCard_eq_empty` via checked fallback,
  `Finset.card_powersetCard`, `Nat.choose_eq_zero_of_lt`, and
  `Finset.card_univ`.

## Agent Notes
- Current `main` is ahead of `origin/main`; do not assume remote is current.
- Do not kill existing Lean/lake checks. If one is running, monitor it passively
  and let it finish.
- Focused tests should cover theorem selector payload hiding/compaction,
  context hydration, generation prompts, verifier classification, semantic
  coverage, context graph generation, and elaborated dependency summary.
