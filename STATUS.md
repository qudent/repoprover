# RepoProver - Status
## Overall direction
Build a cheap, reproducible autoformalization pipeline for the Algebraic Combinatorics gold-standard dataset: select honest source/prefix context, generate Lean statements/proofs without exposing withheld targets, preserve all provider outputs, verify in reusable Lean projects, and iterate from concrete failures. Trust scoring in the dependency graph is deferred until the iterative proof-generation pipeline mostly succeeds.

-------

## Current State
The repo has working source-statement generation, archived provider-result capture, serial reusable-project Lean verification, shape diagnostics, and compiler-feedback repair queues. The strict hard six-row slice is cumulatively 6/6 verified for `$0.21569744`, but that result used target-comment/oracle-ish context surfaces. A new `--context-mode source-only` removes target Lean doc comments, target-derived comment labels, hidden-name guidance triggers, and imported source-label API retrieval for more realistic validation.

Key run directory: `docs/source-statement-runs/2026-05-05-strict-guidance-six-generation/`.
Main reports: `docs/source-statement-strict-guidance-six-generation-report.md` and `docs/source-statement-realistic-context-mode-report.md`.

## Active Goals
- [x] Push the strict hard six-row slice from 4/6 to 6/6 with cheap targeted repairs.
- [x] Add a realistic source-only prompt mode to separate context-selection work from target-comment debugging.
- [ ] Keep all paid OpenRouter results recoverable in git artifacts before Lean checking.
- [ ] Keep `STATUS.md` compact; use reports and git history for durable audit details.

## TODO Plan
- [ ] Build a TeX-derived focus selector so `source-only` prompts can recover useful subtask cues without target Lean comments/names.
- [ ] Run future paid validation in `source-only` mode first; keep `target-comment` only as a diagnostic comparison.
- [ ] Keep trust scoring deferred until larger slices mostly succeed.

## Blockers
- The overall textbook-scale pipeline is not ready for trust scoring; larger slices still fail too often, and realistic context selection is not yet strong enough.

## Recent Results
- Targeted guidance over the six remaining 11-row failures produced 0/6; strict guidance improved that to 2/6 first pass.
- Compiler/shape repairs recovered rows 6 and 5, bringing the strict hard slice to 4/6.
- Added repair-domain guidance for negative-binomial helper application and finite `finsum` support-subset failures; focused tests pass (`58 passed` for source-statement artifact/prompt tests).
- Regenerated shape diagnostics so row 3 no longer gets a false finite-composition warning; only the already-repaired row 5 group-power warning remains.
- Repair attempt 3 for rows 2 and 3 completed with 2/2 parsed outputs, 2 paid calls, `$0.012440043` actual cost, and both rows verified.
- `source-only` budget checkpoints were generated for the strict 6-row and broader 11-row slices at `$0.00`; estimated max generation costs are `$0.17953842` and `$0.329193645`.

## Agent Notes
- A 72-record local preflight was stopped because it spent about 30 minutes compiling heavy modules without final row results. Treat long preflight runtime as a scaling issue; do not run larger Lean preflights without better module/build reuse.
