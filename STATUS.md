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
- [x] Validate transitive local predecessor context on a fresh multi-unit slice.
- [ ] Run a fixed model/context ablation on the same theorem-level panel:
  DeepSeek V4 Flash vs DeepSeek V4 Pro vs Kimi K2.6, with identical hidden-target
  context packs and acceptance metrics.

## Blockers
- Previous-project context is the strongest signal, but aligned target
  declarations for the selected source unit must remain hidden.
- Broad theorem units can require same-unit helper definitions and proofs;
  `prop.sf.Npar-as-par` remains a hard proof-synthesis case.
- Selectors still invent or miss Mathlib/project APIs; Lean hydration catches
  many but not all such gaps.
- Some remaining failures are now real proof-shape issues after context improves,
  for example raw Catalan proof tactics treating predicates as binders.
- Flash-heavy generation is not yet justified as an optimizer strategy; it is
  only the cheap baseline. Need same-panel model ablations before concluding
  whether Flash, Pro, or Kimi should own selector/generator/proof-lane stages.
- Full elaborated dependency extraction is useful but heavy on this 8 GB
  machine; reuse `docs/lean-elaborated-direct-deps.jsonl` unless a rerun is
  necessary.

## Recent Results
- Scale snapshot: 462 LaTeX source units, 114 gold-candidate units, 414 aligned
  Lean declarations. Elaborated direct deps over gold units have median 44
  Mathlib and 5 project constants per unit.
- Current dev-panel proof-lane acceptance is `3/5` compiled and `3/5` semantic.
  The new fresh-slice transitive-localdeps run regressed to `0/5` compiled and
  `0/5` semantic after ordinary generation. Selector cost was `$0.00502572`,
  ordinary generation cost was `$0.006082748`, and proof-lane generation cost
  was `$0.009473072`.
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
- Fresh-slice proof-lane acceptance at
  `docs/latex-statement-proof-lane-acceptance-runs/2026-05-06-fresh-slice5-transitive-localdeps-v1-assumption-paid-v1/`
  made no paid calls itself, found no leakage-scan matches, and ended at `0/5`:
  3 clean declines and 2 compile failures. Unit 002 still used bad `IsUnit`
  construction/subscript notation; unit 004 referenced missing `toSign` and
  `allEvenTuples` context and hit a heartbeat timeout.
- Generic honesty fixes landed: placeholder-bodied local predecessor snippets
  are dropped from prompt/support context, proof-lane generation can resume
  completed batches, and provider exceptions are logged per batch.
- Codex-log audit for the previous eight-hour report is committed at
  `reports/REPORT-20260506T053800Z-codex-log-audit.md`; it used
  `/home/name/.codex/log/codex-tui.log` and native session JSONL under
  `/home/name/.codex/sessions`.
- Follow-up validation report is in
  `reports/REPORT-20260506T0615Z-codex-log-audit-followup.md`; it confirms the
  prior audit used native Codex logs, refines the missing-main-JSONL caveat, and
  did not run provider calls or Lean verification.

## Agent Notes
- Current `main` is ahead of `origin/main`; do not assume remote is current.
- Do not kill existing Lean/lake/Codex checks.
- Benchmark claims should use a fresh slice; current dev/fresh panels are
  development evidence.
- Next useful work: run the fixed model/context ablation panel, then route
  failures by class. Avoid another Flash-only loop unless it is a cheap dry-run
  gate before a stronger model comparison.
