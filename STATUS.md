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
- [ ] Add second-round Mathlib lookup/repair for selector guesses that hydrate
  as unknown constants.

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

## Agent Notes
- Current `main` is ahead of `origin/main`; do not assume remote is current.
- Do not kill existing Lean/lake checks. If one is running, monitor it passively
  and let it finish.
- Focused tests should cover theorem selector payload hiding/compaction,
  context hydration, generation prompts, verifier classification, semantic
  coverage, context graph generation, and elaborated dependency summary.
