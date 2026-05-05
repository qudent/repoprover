# RepoProver - Status
## Overall direction
Build a cheap, reproducible source-to-Lean autoformalization pipeline for the Algebraic Combinatorics dataset: honest source/prefix context, recoverable provider outputs, reusable Lean verification, and failure-driven context/repair iteration. Trust scoring is deferred until realistic source-only slices mostly succeed.

-------

## Current State
The strict 6-row hard slice reached 6/6, but that used target-comment context and is debugging evidence only. The current validation path is `--context-mode source-only`, which withholds target Lean statements/names, removes target doc-comment and target-label focus, and uses visible TeX/source spans plus Lean prefix/local API context.

## Active Goals
- [ ] Keep every paid OpenRouter output recoverable in git before Lean checking.
- [ ] Improve realistic context selection before spending on larger runs.
- [ ] Use broader source-only slices as the main evidence, not the old six-row loop.

## TODO Plan
- [x] Add source-only prompt mode and TeX-derived focus.
- [x] Run and repair an 11-record source-only validation slice.
- [x] Add TeX environment-balance span expansion.
- [x] Add same-file source-label local API retrieval.
- [ ] Next zero/low-cost step: improve theorem-family selection for broad source spans.

## Blockers
- Source-only context still often lacks the exact theorem-family cue: target-comment focus terms are absent from visible source spans in `7/11` broader rows.
- A 72-record preflight was too slow with current Lean setup; keep validation slices bounded until verification reuse is improved.

## Recent Results
- Source-only 11-row generation plus compile repair reached `4/11` for about `$0.153232781`.
- Balanced-span rerun cost `$0.126677307`, still `1/11`; shape repairs cost `$0.020500999` and did not add passes.
- Latest zero-cost budget regeneration shows row 11 now receives same-file source-label helpers (`simpleTransposition_*`) without hidden target names; focused tests pass with `71 passed`.

## Agent Notes
- Do not run more paid calls until the next context-selection improvement is clear and budgeted.
- Current prompt improvements are generic infrastructure; row-specific repair guidance remains isolated as failure-driven diagnostics, not scale evidence.
