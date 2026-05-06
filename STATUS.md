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
development loop is a fixed five-unit panel plus fresh five-unit slices.

## Active Goals
- [ ] Use LaTeX statement units as the main planning and benchmark surface.
- [ ] Keep paid selector/generation outputs recoverable before verification.
- [ ] Select and hydrate source/project/local/Mathlib context without hidden
  target leakage.
- [ ] Route remaining clean declines by failure class: context acquisition,
  Mathlib hydration, or proof synthesis.

## TODO Plan
- [x] Generate theorem-level source units and gold-candidate rows.
- [x] Add target-blind selector, hydrator, generator, verifier, gold comparison,
  semantic grading, repair loops, failure taxonomy, and contract normalization.
- [x] Add fixed dev/fresh five-unit panels and one-command panel runs.
- [x] Add target-hidden proof-lane task generation, paid proof-lane generation,
  no-provider acceptance, and overlay verification.
- [x] Mine clean proof-lane declines against source-visible project declarations.
- [x] Turn decline-context mining into prompt-safe context acquisition packs.
- [x] Run the packed fresh-slice proof-lane payload as a paid/checked experiment
  after the target-clean gate passed.
- [x] Add a no-provider partial-proof diagnostic for raw contract-violating
  proof-lane outputs.
- [x] Add a bounded dependency-closure variant of decline context packs and
  local diagnostics for the Catalan partial proof.
- [ ] Validate the next generic context/proof-lane change on a fresh slice, not
  only on NPartition or one already-debugged theorem.

## Blockers
- Previous-project context is the strongest signal, but aligned target
  declarations for the selected source unit must remain hidden.
- Broad theorem units can require same-unit helper definitions and proofs;
  `prop.sf.Npar-as-par` remains a hard proof-synthesis case.
- Selectors still invent or miss Mathlib/project APIs; Lean hydration catches
  many but not all such gaps.
- Some remaining failures are likely context acquisition, not reasoning:
  existing project declarations were mentioned by the model but not selected as
  usable declarations.
- Full elaborated dependency extraction is useful but heavy on this 8 GB
  machine; reuse `docs/lean-elaborated-direct-deps.jsonl` unless a rerun is
  necessary.

## Recent Results
- Scale snapshot: 462 LaTeX source units, 114 gold-candidate units, 414 aligned
  Lean declarations. Elaborated direct deps over gold units have median 44
  Mathlib and 5 project constants per unit.
- Current dev-panel acceptance after proof-lane retries is `3/5` compiled and
  `3/5` semantic coverage. Total dev-panel proof-lane generation spend for the
  recent sequence was `$0.00598472`.
- Fresh-slice proof-lane generation cost `$0.00687388` and returned four
  contract-clean declines; acceptance stayed `1/5` compiled and `1/5` semantic.
- New source-only decline-context report:
  `docs/latex-statement-proof-lane-decline-context-2026-05-06.md`. It scanned
  5,677 project declarations in 53 project Lean files across 6 clean-decline
  units: 15 identifiers were project-source matches mentioned but not selected,
  11 were already selected, and 14 were absent from the project index.
- Prompt-safe decline-context pack:
  `docs/latex-statement-proof-lane-decline-context-pack-2026-05-06.md`. It uses
  gold only as an exclusion filter, selected 18 extra project-context snippets,
  and generated no-provider proof-lane payloads. Fresh-slice payloads attach
  context to 3/4 tasks; dev-panel payloads attach 0/2.
- Packed-context paid fresh-slice retry:
  `docs/latex-statement-proof-lane-generation-runs/2026-05-06-fresh-slice5-decline-context-paid-v1/`
  cost `$0.00568302` for 3 context-bearing units. Acceptance at
  `docs/latex-statement-proof-lane-acceptance-runs/2026-05-06-fresh-slice5-decline-context-paid-v1/`
  stayed `1/5` compiled and `1/5` semantic with 3 clean declines and no task
  leakage matches.
- The proof-lane prompt now forbids saying a declaration is missing when it is
  present in `decline_context_pack.selected_project_context`; declines must
  identify dependency/import/signature/proof-synthesis blockers. Packed budget
  payloads were regenerated with this generic instruction.
- A one-unit stricter-prompt paid probe on fresh `unit-001` cost `$0.00222572`.
  It used the acquired LGV declarations in a partial Catalan proof sketch but
  violated the contract by returning `cannot_prove_from_visible_context` with a
  nonempty Lean body and `sorry`; contract enforcement normalized it to a clean
  decline.
- Partial-proof diagnostic:
  `docs/latex-statement-partial-proof-diagnostics/2026-05-06-fresh-unit001-stricter-prompt/`
  filters source-module imports transitively, materializes visible support, and
  checks the raw Catalan body locally. Result: `lean_errors_before_or_at_placeholder`,
  `1/15` support snippets accepted, 12 Lean errors before the final `sorry`;
  blocker is context dependency closure plus proof synthesis.
- Dependency-closure pack:
  `docs/latex-statement-proof-lane-decline-context-pack-closure-2026-05-06.json`
  adds 55 dependency rows across 6 decline units; Catalan grows to 42 context
  rows with 26 dependencies. The local closure diagnostic at
  `docs/latex-statement-partial-proof-diagnostics/2026-05-06-fresh-unit001-closure-pack/`
  still fails (`lean_errors_before_or_at_placeholder`): 49 candidates, 0 accepted
  under a 10s per-snippet timeout, and remaining unknown Catalan/path-matrix
  identifiers. Body-snippet copying is too noisy/slow for same-file context.
- Codex-log audit for the previous eight-hour report is committed at
  `reports/REPORT-20260506T053800Z-codex-log-audit.md`; it used
  `/home/name/.codex/log/codex-tui.log` and a native session JSONL under
  `/home/name/.codex/sessions`.

## Agent Notes
- Current `main` is ahead of `origin/main`; do not assume remote is current.
- Do not kill existing Lean/lake/Codex checks.
- Benchmark claims should use a fresh slice; current dev/fresh panels are
  development evidence.
- Next useful work: replace arbitrary body-snippet materialization with a
  target-hidden signature/assumption prelude or redacted-prefix module for
  previous declarations, then route remaining partial raw bodies to a stronger
  proof-synthesis/repair lane. Do not keep spending ordinary proof-lane calls on
  the same prompt shape.
