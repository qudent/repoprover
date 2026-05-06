# RepoProver - Status
## Overall Direction
Build a cheap, reproducible source-LaTeX-to-Lean autoformalization pipeline for
Algebraic Combinatorics. The production unit is one LaTeX theorem/environment,
planned into one or more Lean declarations with selected source, previous
book/source, previous project declarations/definitions/notations/instances,
local file/import/style context, and selected Mathlib APIs, then checked by Lean
plus post-hoc semantic coverage.

-------

## Current State
The repo has pivoted from declaration rows to theorem-level LaTeX statement
rows. Main datasets are `docs/latex-statement-units.jsonl` and
`docs/latex-statement-gold-candidates.jsonl`; old declaration-level artifacts
are preserved at `checkpoint/before-per-latex-statement-dataset`. Active work is
now on target-hidden context acquisition and proof-lane repair, using fixed
dev/fresh panels plus one-off diagnostics.

## Active Goals
- [ ] Keep LaTeX statement units as the main planning and benchmark surface.
- [ ] Keep paid selector/generation outputs recoverable before verification.
- [ ] Select and hydrate source/project/local/Mathlib context without hidden
  target leakage.
- [ ] Route remaining failures by class: context acquisition, Mathlib hydration,
  or proof synthesis.

## TODO Plan
- [x] Generate theorem-level source units and gold-candidate rows.
- [x] Add selector, hydrator, generator, verifier, semantic grader, repair loops,
  proof-lane tasks, and contract normalization.
- [x] Mine clean proof-lane declines against source-visible project declarations.
- [x] Add prompt-safe decline-context packs and no-provider partial-proof
  diagnostics.
- [x] Add bounded project dependency-closure packs, assumption/signature prelude
  diagnostics, and duplicate/already-imported support filtering.
- [x] Add bounded transitive local predecessor dependency collection; Catalan
  budget payload now includes private `translateVertex`/`dyckDigraph_arc_translate`.
- [ ] Validate the next proof/context change on a fresh multi-unit slice, not
  only on NPartition or one already-debugged theorem.

## Blockers
- Previous-project context is the strongest signal, but aligned target
  declarations for the selected source unit must remain hidden.
- Broad theorem units can require same-unit helper definitions and proofs;
  `prop.sf.Npar-as-par` remains a hard proof-synthesis case.
- Selectors still invent or miss Mathlib/project APIs; Lean hydration catches
  many but not all such gaps.
- Some remaining failures are now real proof-shape issues after context improves,
  for example raw Catalan proof tactics treating predicates as binders.
- Full elaborated dependency extraction is useful but heavy on this 8 GB
  machine; reuse `docs/lean-elaborated-direct-deps.jsonl` unless a rerun is
  necessary.

## Recent Results
- Scale snapshot: 462 LaTeX source units, 114 gold-candidate units, 414 aligned
  Lean declarations. Elaborated direct deps over gold units have median 44
  Mathlib and 5 project constants per unit.
- Current dev-panel proof-lane acceptance is `3/5` compiled and `3/5` semantic;
  current fresh-slice acceptance is `1/5` compiled and `1/5` semantic. Recent
  paid proof-lane spend was under two cents total across the recorded probes.
- Decline-context mining scanned 5,677 project declarations across 53 project
  Lean files. It found source-visible project declarations the model mentioned
  but had not selected, then packed them with gold used only as an exclusion
  filter.
- Best current Catalan diagnostic is
  `docs/latex-statement-partial-proof-diagnostics/2026-05-06-fresh-unit001-assumption-signature-d3-field-tight/`:
  41/41 support assumptions accepted, 7 Lean errors remain. Earlier namespace,
  duplicate, and noisy fallback failures are mostly cleared; `translateVertex`
  was still missing from the old prompt payload.
- New budget-only context-selection artifact
  `docs/latex-statement-context-selection-runs/2026-05-06-catalan-transitive-local-deps-budget/`
  proves the local predecessor collector now exposes `translateVertex`,
  `dyckDigraph_arc_translate`, and the `translatePath_*` family in source order
  before the Catalan target line.
- Codex-log audit for the previous eight-hour report is committed at
  `reports/REPORT-20260506T053800Z-codex-log-audit.md`; it used
  `/home/name/.codex/log/codex-tui.log` and native session JSONL under
  `/home/name/.codex/sessions`.

## Agent Notes
- Current `main` is ahead of `origin/main`; do not assume remote is current.
- Do not kill existing Lean/lake/Codex checks.
- Benchmark claims should use a fresh slice; current dev/fresh panels are
  development evidence.
- Next useful work: rerun a small fresh proof-lane payload with the transitive
  local predecessor context, then route surviving errors to proof repair rather
  than another unchanged ordinary generation call.
