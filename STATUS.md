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
- [x] Run the next paid check as a fresh slice, not another single
  already-debugged theorem.
- [x] Add bridge-aware semantic grading so equivalent source/gold surfaces do
  not look like failures.
- [x] Filter repair prompts to only unresolved unit keys and stop recoverably on
  invalid repair-context JSON.
- [x] Add a targeted proof-lane overlay utility for merging one-unit repairs
  back into a panel/slice artifact without losing hidden-target filtering.
- [x] Add target-hidden proof-lane dossier generation for clean declines.
- [x] Add a no-provider proof-lane acceptance runner that overlays solutions,
  verifies, and runs post-hoc grading.
- [x] Route dev-panel clean declines and current-verifier compile failures
  through a proof-synthesis/coding-agent lane.
- [ ] Route remaining hard clean declines through stronger proof synthesis or
  better project/local context acquisition.

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
- Latest merged dev-panel artifact:
  `docs/latex-statement-repair-loop-runs/2026-05-06-dev-panel5-v2-repair-v5-merged-panel/`.
  Effective provider cost for the artifact path: `$0.0244708072`.
  Generated-only verification is `3/5` compiled with `2` clean declines and no
  compile failures; semantic coverage is `3/5` units after a generic
  grader-side pointwise-hypothesis bridge proved both triangular aligned gold
  declarations from the generated `BlockTriangular` disjunction theorem.
- A focused triangular source-shape repair probe cost `$0.00171864` and
  returned the same compiled theorem shape, confirming the prior failure was a
  semantic-grader false reject under theorem-implication grading.
- Fresh five-unit slice:
  `docs/latex-statement-fresh-slice-2026-05-06.json`; summary:
  `docs/latex-statement-fresh-slice-2026-05-06-summary.md`. Paid selector plus
  generation cost `$0.0127524416`. Raw verification was `0/5`, but two generic
  verifier fixes (scoped visible-support variables and semantic reuse of
  verified opens) reran no-cost to `1/5` generated-only compile and `1/5`
  semantic coverage.
- Fresh-slice repair follow-up: first paid repair-context call cost
  `$0.00738948` but truncated at the 4k output cap. The compact 8k v2 run at
  `docs/latex-statement-repair-loop-runs/2026-05-06-fresh-slice5-repair-v1-paid-v2-compact/`
  cost `$0.01428308`, selected valid target-hidden context, hydrated 8 checked
  signatures plus 2 fallback-resolved requests, and preserved `unit-002`; final
  verification stayed `1/5` with 3 clean declines and 1 signed-sum compile
  failure from the bad `Fin d -> ℤ` carrier choice.
- Targeted signed-sum proof-lane retry cost `$0.00240898` and, after a generic
  finite-choice-space prompt rule, converted the compile failure into a clean
  decline with the correct diagnosis: the source carrier is finite sign vectors
  `Fin d -> ZMod 2`, not all `Fin d -> ℤ`. The merged artifact
  `docs/latex-statement-repair-loop-runs/2026-05-06-fresh-slice5-unit004-finiteness-merged/`
  verifies `1/5` compiled, `4/5` clean declines, and semantic coverage `1/5`.
- Target-hidden proof-lane dossiers are now generated for clean declines:
  4 fresh-slice units in
  `docs/latex-statement-proof-lane-tasks/2026-05-06-fresh-slice5-finiteness-merged/`
  and 2 dev-panel units in
  `docs/latex-statement-proof-lane-tasks/2026-05-06-dev-panel5-v2-merged-panel/`.
  The task schema strips aligned targets and post-hoc semantic check/count
  metadata; leakage scans found no hidden target names.
- Proof-lane acceptance is now a reproducible stage:
  `scripts/run_latex_statement_proof_lane_acceptance.py` validates solution
  unit keys against the target-hidden task set, scans tasks for forbidden
  post-hoc metadata, overlays solutions onto the base run, verifies with
  target-blind context/materialized support, and writes exact plus semantic
  grader summaries. No-cost smoke artifact:
  `docs/latex-statement-proof-lane-acceptance-runs/2026-05-06-fresh-slice5-unit004-finiteness-smoke/`
  reproduced the signed-sum merge result: `1/5` compiled, `1/5` semantic
  coverage, solution unit `unit-004` still a clean decline.
- Proof-lane generation is now scripted in
  `scripts/run_latex_statement_proof_lane_generation.py`. Budget payloads were
  generated for the four fresh-slice proof-lane tasks and the two original
  dev-panel proof-lane tasks. A paid dev-panel proof-lane run cost
  `$0.00311878` and cleanly declined both FPS division and NPartition. Running
  the current verifier through acceptance then exposed a stale dev-panel
  false-positive: triangular determinant omitted visible `K`/`[CommRing K]`
  binders and fell to `2/5`. A generic missing-typeclass-binder instruction plus
  one focused paid retry cost `$0.00144802` and restored triangular determinant:
  current dev-panel acceptance is `3/5` compiled and `3/5` semantic coverage.
- Codex-log audit for the previous eight-hour report is committed at
  `reports/REPORT-20260506T053800Z-codex-log-audit.md`. Main recommendation:
  stop single-theorem loops once the failure class stops changing and run a
  panel/default summary instead.

## Agent Notes
- Current `main` is ahead of `origin/main`; do not assume remote is current.
- Do not kill existing Lean/lake/Codex checks. A separate CauchyBinet
  diagnostic Codex/Lean task is still expected to be left alone.
- Next useful work: route remaining panel failures by class. FPS division and
  NPartition on the dev panel, plus signed-sum and normalized-`sorry` declines
  on the fresh slice, need proof-synthesis/coding-agent lanes rather than more
  selector prompt tuning. Use a new fresh slice for benchmark claims; the
  current fresh slice is development evidence now.
