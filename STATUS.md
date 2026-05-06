# RepoProver - Status
## Overall Direction
Build a cheap, reproducible source-to-Lean autoformalization pipeline for
Algebraic Combinatorics. The production unit is one LaTeX theorem/environment,
planned into one or more Lean declarations with selected source/project/local
and Mathlib context, then checked by Lean plus post-hoc semantic coverage.

-------

## Current State
The repo has pivoted from declaration-level rows to theorem-level LaTeX
statement rows. Current datasets are `docs/latex-statement-units.jsonl` and
`docs/latex-statement-gold-candidates.jsonl`; old declaration-level artifacts
are preserved at `checkpoint/before-per-latex-statement-dataset`.

## Active Goals
- [ ] Use LaTeX statement units as the main planning and benchmark surface.
- [ ] Keep paid selector/generation outputs recoverable before verification.
- [ ] Select source text, previous book/source statements, previous project
  declarations, local file/import/style context, and Mathlib APIs separately.
- [ ] Make theorem-level semantic coverage and repair loops reliable on broader
  batches without benchmark leakage or hardcoded theorem-specific hints.

## TODO Plan
- [x] Generate theorem-level source units and gold-candidate rows.
- [x] Add Lean-tooling hydration for selector-requested and fallback Mathlib
  names.
- [x] Add theorem-level generation, generated-only verification, exact-name
  comparison, semantic coverage grading, and bounded repair loops.
- [x] Add same-file local predecessor declaration context with target omitted.
- [x] Make semantic-aware repair continue after compile-clean but
  coverage-partial runs using only source-unit keys from post-hoc coverage.
- [x] Fix semantic-grader false redeclarations when checking multiple aligned
  gold declarations for one source unit.
- [ ] Reclassify old strict-grader mismatches into `compile_failure`,
  `missing_context`, `wrong_math`, `shape_mismatch_against_oracle`, or
  `useful_alternative_formalization`.
- [ ] Scale the mixed-batch loop beyond the current determinant/symmetric
  probes and reduce noisy fallback-context candidates.
- [x] Run a paid diverse4 theorem-level probe outside the recent
  determinant/symmetric examples: Vandermonde, LGV binomial unimodality,
  Boolean Möbius inversion, and partition bijection.
- [x] Reduce noisy fallback Mathlib candidates and add per-unit generation
  splitting after the diverse4 batch exposed context/noise and JSON-cap issues.
- [x] Strip Lean comments from project/local snippets and redact failed exact
  identifiers before generation prompts to avoid future-label/name leakage.

## Blockers
- Previous-project context is the strongest signal, but it must stay
  target-blind: aligned target declarations for the selected source unit remain
  hidden from selector/generator prompts.
- Selector/generator still sometimes understand the math but miss Lean shapes:
  omitted ambient binders/typeclasses, nonexistent Mathlib names, or one broad
  task where multiple Lean declarations are needed.
- The semantic-aware loop currently uses post-hoc coverage only to choose unit
  keys for review. That is benchmark-honest enough for repair control, but it
  must be documented separately from source-only generation success.
- Full Lean dependency extraction is feasible but heavy on this 8 GB machine;
  reuse `docs/lean-elaborated-direct-deps.jsonl` unless a rerun is necessary.
- Current paid probe target:
  `docs/latex-statement-context-runs/2026-05-06-diverse4-v1-paid/` with
  matching generation/repair artifacts if the initial run is informative.
- Diverse4 shows the next real blocker: selector-level context is too weak for
  broad nontrivial units. Transport is better after filtering/splitting, but
  Lean coverage stayed `0/4`.

## Recent Results
- Dataset scale: 462 LaTeX source units, 114 gold-candidate units, 414 aligned
  Lean declarations; median 2 aligned declarations per gold unit, p90 8, max
  29.
- Elaborated dependency summary over 114 units: median 44 direct Mathlib
  constants and median 5 direct project constants per unit.
- Symmetric `e_n = 0`: autonomous repair-context loop reached compile `1/1`
  and semantic coverage `1/1`; extra autonomous loop cost `$0.02180284`.
- Triangular determinant: fallback hydration recovered
  `Matrix.det_of_upperTriangular`/`Matrix.det_of_lowerTriangular`; bounded loop
  repaired syntax/metadata in one round and proved semantic coverage `2/2`;
  added cost `$0.00550774`.
- Mixed determinant batch (`thm.det.transp`, `thm.det.triang`,
  `cor.det.sig-row-col`): initial generation compiled `0/3`; compile repair
  reached `3/3`; semantic-aware repair plus grader redeclaration fix now gives
  generated-only compile `3/3` and semantic coverage `3/3` source units with
  `5/5` aligned gold declarations proved. Total paid cost `$0.03507336`.
- Diverse4 broader batch (`cor.lgv.binom-unimod`, Vandermonde NN, Boolean
  Möbius, partition bijection): selector valid JSON, but `4/4` exact Mathlib
  guesses failed. Initial generation and two repair rounds compiled `0/4`.
  Fallback filtering cut candidates from 32 to 10; split generation returned
  valid JSON for all four one-unit calls but still compiled `0/4`. Total paid
  diverse4 diagnostic spend so far is about `$0.03718`.
- Focused theorem-level suite passed: 61 pytest tests plus `py_compile` over
  the selector/generator/repair/verifier scripts.

## Agent Notes
- Current `main` is ahead of `origin/main`; do not assume remote is current.
- Do not kill existing Lean/lake checks. Monitor passively and let them finish.
- Focused tests should cover theorem selector payload hiding/compaction,
  context hydration, generation prompts, verifier classification, semantic
  coverage, context graph generation, and elaborated dependency summary.
