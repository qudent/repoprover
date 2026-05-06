# RepoProver - Status
## Overall Direction
Build a cheap, reproducible source-LaTeX-to-Lean autoformalization pipeline for
Algebraic Combinatorics. The production unit is one LaTeX theorem/environment,
planned into one or more Lean declarations with selected source, previous
book/source, previous project, local file/import/style, and Mathlib context,
then checked by Lean plus post-hoc semantic coverage.

-------

## Current State
The repo has pivoted from declaration rows to theorem-level LaTeX statement
rows. Main datasets are `docs/latex-statement-units.jsonl` and
`docs/latex-statement-gold-candidates.jsonl`; old declaration-level artifacts
are preserved at `checkpoint/before-per-latex-statement-dataset`. The active
development loop is now a fixed five-unit panel rather than a single theorem.

## Active Goals
- [ ] Use LaTeX statement units as the main planning and benchmark surface.
- [ ] Keep paid selector/generation outputs recoverable before verification.
- [ ] Select source/project/local/Mathlib context separately and hydrate
  Mathlib requests with Lean tooling before generation.
- [ ] Make repair loops reliable on broader batches without theorem-specific
  prompt hints or hidden target leakage.

## TODO Plan
- [x] Generate theorem-level source units and gold-candidate rows.
- [x] Add target-blind selector, hydrator, generator, verifier, gold comparison,
  semantic grading, repair loops, failure taxonomy, and contract normalization.
- [x] Add a fixed five-unit dev panel for richer loop feedback.
- [x] Add a one-command panel runner that performs selector -> hydration ->
  generation -> verification -> summary.
- [ ] Run the next paid check as a panel or fresh-heldout slice, not another
  single already-debugged theorem.
- [x] Add bridge-aware semantic grading so equivalent source/gold surfaces do
  not look like failures.
- [ ] Route cases with checked context but repeated clean declines to a proof
  synthesis/coding-agent lane instead of more selector prompt tuning.

## Blockers
- Previous-project context is the strongest signal, but aligned target
  declarations for the selected source unit must remain hidden.
- Broad theorem units can require new same-unit helper definitions and proofs;
  `prop.sf.Npar-as-par` remains the hard dev case.
- Selectors still invent Mathlib/project API names; Lean hydration catches many
  and can recover some bridge facts, but not all project-specific context.
- Generators can still sketch incomplete helper proofs, as in NPartition.
- Full elaborated dependency extraction is useful but heavy on this 8 GB
  machine; reuse `docs/lean-elaborated-direct-deps.jsonl` unless a rerun is
  necessary.

## Recent Results
- Scale snapshot: 462 LaTeX source units, 114 gold-candidate units, and 414
  aligned Lean declarations; elaborated direct deps over gold units have median
  44 Mathlib and 5 project constants per unit.
- Attempt-level taxonomy across recorded theorem runs: 16 compiled / 73 unit
  checks; deduplicated by source unit, 6/11 touched units have compiled at least
  once.
- Five-unit panel artifacts:
  `docs/latex-statement-dev-panel-2026-05-06.json` and
  `docs/latex-statement-dev-panel-2026-05-06-summary.md`.
- Panel runner baseline: initial paid generation compiled `1/5`; visible
  support rerun compiled `2/5` and semantically covered inverse uniqueness
  `1/5`.
- Vandermonde bridge retry proved the source range-sum theorem and the
  bridge-aware semantic grader proved its aligned antidiagonal gold theorem.
- Latest merged panel artifact:
  `docs/latex-statement-repair-loop-runs/2026-05-06-dev-panel5-v2-repair-v5-merged-panel/`.
  Effective provider cost for the artifact path: `$0.0244708072`.
  Generated-only verification is `3/5` compiled with `2` clean declines and no
  compile failures; semantic coverage is `2/5` units.
- Fixed repair-loop orchestration bugs: multi-unit repair outputs are split
  back into per-unit batches, and each split batch carries the original
  unit-specific generation payload so verifier import/support inference stays
  target-blind but complete.
- Added generic bridge-rewrite prompt guidance: when a source theorem exposes a
  checked bridge lemma's left-hand side, rewrite with the source theorem first,
  then apply the bridge rewrite.
- Codex-log audit for the previous eight-hour report is committed at
  `reports/REPORT-20260506T053800Z-codex-log-audit.md`. Main recommendation:
  stop single-theorem loops once the failure class stops changing and run a
  panel/default summary instead.

## Agent Notes
- Current `main` is ahead of `origin/main`; do not assume remote is current.
- Do not kill existing Lean/lake/Codex checks. A separate CauchyBinet
  diagnostic Codex/Lean task is still expected to be left alone.
- Next useful work: route remaining panel failures by class. Triangular needs
  source-shape planning that produces separate upper/lower entrywise-zero
  statements; FPS division and NPartition need proof-synthesis/coding-agent
  lanes rather than more selector prompt tuning. Use a fresh held-out slice for
  benchmark claims.
