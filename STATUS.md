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
- [x] Run a zero-cost 64-record source-only context audit.
- [x] Run paid generation-only on an 8-record easier source-only subset from the 64-row audit.
- [ ] Commit raw easy-8 paid outputs before Lean verification, then verify them serially.

## Blockers
- Source-only context still often lacks exact theorem-family cues: target-comment focus terms are absent from visible source spans in `45/64` broader audit rows.
- The deterministic gold-candidate source spans are usually broad: `62/64` broad, `61/64` multi-environment, `60/64` extra-label rows in the latest audit.
- A 72-record preflight was too slow with current Lean setup; keep validation slices bounded until verification reuse is improved.

## Recent Results
- Source-only 11-row generation plus compile repair reached `4/11` for about `$0.153232781`.
- Balanced-span rerun cost `$0.126677307`, still `1/11`; shape repairs cost `$0.020500999` and did not add passes.
- Latest 64-row budget audit made zero paid calls, estimates max generation cost at `$1.976172810`, has `0` hidden target-name payload hits, and extracts focused labeled environments for `64/64` rows.
- Easy-8 source-only generation made `8/8` paid calls, generated `8/8` parsed declarations, and cost `$0.071505155`; Lean verification has not been run yet.
- Focused tests pass with `75 passed`.

## Agent Notes
- Do not run more paid calls until the next context-selection improvement is clear and budgeted.
- Current prompt improvements are generic infrastructure; row-specific repair guidance remains isolated as failure-driven diagnostics, not scale evidence.
