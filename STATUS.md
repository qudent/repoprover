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
- [ ] Add bridge-aware semantic grading so equivalent source/gold surfaces do
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
- Semantic grading can false-reject equivalent theorem surfaces: Vandermonde
  now compiles as the source range-sum theorem, while the aligned gold theorem
  is Mathlib's antidiagonal shape.
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
- NPartition context work fixed many generic issues (field/projection context,
  list/sort/cardinality bridges, representation control, placeholder
  normalization) but still ends in clean declines or incomplete helper skeletons.
- Five-unit panel artifacts:
  `docs/latex-statement-dev-panel-2026-05-06.json` and
  `docs/latex-statement-dev-panel-2026-05-06-summary.md`.
- Five-unit selector comparison:
  default DeepSeek V4 Flash returned valid JSON in 115.186s for `$0.003094084`
  with 6,914 reasoning tokens; no-reasoning returned valid JSON in 33.785s for
  `$0.00300286` but had worse exact API recall. Hydration confirms no-reasoning
  is useful for cheap triage, while failed/high-risk units should be escalated.
- `scripts/run_latex_statement_panel.py` now runs the fixed panel as a
  repeatable stage chain and writes `eval/panel-summary.{json,md}`. No-cost
  smoke artifacts:
  `docs/latex-statement-panel-runs/2026-05-06-dev-panel5-runner-budget/` and
  `docs/latex-statement-panel-runs/2026-05-06-dev-panel5-runner-generation-budget/`.
- First paid panel-runner pass:
  `docs/latex-statement-panel-runs/2026-05-06-dev-panel5-runner-paid-v1/`.
  Generation cost `$0.0051861712` for 35,188 prompt tokens and 2,057 completion
  tokens. Verification compiled 1/5 units; failures were 2 compile failures and
  2 clean declines. Semantic coverage proved 0/5 aligned gold units.
- Visible-support rerun of the same paid generation:
  `docs/latex-statement-panel-runs/2026-05-06-dev-panel5-runner-paid-v1-visible-support/`.
  No provider calls; local verification took 508.903s. Compile improved to 2/5
  and semantic coverage to 1/5: inverse uniqueness is a true win once visible
  project definitions are materialized.
- Vandermonde bridge retry:
  `docs/latex-statement-generation-runs/2026-05-06-dev-panel-vandermonde-bridge-v2-paid/`.
  Cost `$0.0013226`; generated-only verification compiled `1/1` after generic
  Finset binder-syntax guidance and inferred-open validation. Post-hoc semantic
  coverage remains `0/1` because gold is antidiagonal while the generated theorem
  is the LaTeX range-sum form; this is a grader-surface caveat, not missing
  context.
- Codex-log audit for the previous eight-hour report is committed at
  `reports/REPORT-20260506T053800Z-codex-log-audit.md`. Main recommendation:
  stop single-theorem loops once the failure class stops changing and run a
  panel/default summary instead.

## Agent Notes
- Current `main` is ahead of `origin/main`; do not assume remote is current.
- Do not kill existing Lean/lake/Codex checks. A separate CauchyBinet
  diagnostic Codex/Lean task is still expected to be left alone.
- Next useful work: route remaining panel failures by class. Vandermonde needs
  bridge-aware semantic grading; triangular needs stronger target-shape
  planning; FPS division and NPartition remain proof/context synthesis cases.
