# RepoProver - Status
## Overall direction
Build a cheap, reproducible autoformalization pipeline for the Algebraic Combinatorics gold-standard dataset: choose honest source/prefix context, generate Lean without exposing withheld targets, preserve provider outputs, verify in reusable Lean projects, and iterate from concrete failures. Trust scoring is deferred until larger realistic-context slices mostly succeed.

-------

## Current State
Source-statement generation, archived provider-result capture, reusable-project verification, shape diagnostics, and repair queues are implemented. The strict six-row hard slice reached 6/6, but it used target-comment context and is not strong evidence for full-book scaling. The current validation path is `--context-mode source-only`, which removes target Lean doc comments, target-derived labels, hidden-name guidance triggers, and imported source-label API retrieval.

## Active Goals
- [ ] Keep all paid OpenRouter outputs recoverable in git artifacts before Lean checking.
- [ ] Validate source-only context on broader slices before adding trust scoring.
- [ ] Improve source/TeX focus selection rather than hand-tuning the six hard rows.

## TODO Plan
- [x] Add TeX-derived `tex_source_focus` to source-only prompts.
- [x] Run an 11-record source-only generation pass.
- [x] Commit the raw 11-record paid generation artifacts.
- [x] Verify the 11 generated files serially in a reusable Lean project and record per-row outcomes.
- [ ] Use the source-only failures to improve source/TeX focus selection and generic repair prompts.

## Blockers
- Realistic context selection is still weak: context comparison found target-comment focus terms absent from source-only spans in 7/11 broader rows.
- Larger Lean preflights are too slow with current module/build reuse; a 72-record preflight was stopped after about 30 minutes without final row results.

## Recent Results
- Added `source-only` prompt mode and context-mode comparison artifacts; hidden target-name hits are 0 on the strict 6 and broader 11 prompt sets.
- Added TeX-derived focus cues from visible source only: labels, refs, theorem-like environments, part markers, keyword cues, excerpts, and broad-span risk flags.
- Completed an 11-record source-only generation-only run with DeepSeek V4 Pro: 11/11 generated, `$0.081084638`.
- Verified the 11 generated files serially: 1/11 passed, 8 failed generated-only compilation, and 2 compiled but did not prove the withheld gold statement.

## Agent Notes
- Raw paid generation is committed in `2206e80`; verification artifacts are committed in `ea48ce5`.
