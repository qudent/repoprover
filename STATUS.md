# RepoProver - Status
## Overall direction
Build a cheap, reproducible autoformalization pipeline for the Algebraic Combinatorics gold-standard dataset: select honest source/prefix context, generate Lean statements/proofs without exposing withheld targets, preserve all provider outputs, verify in reusable Lean projects, and iterate from concrete failures. Trust scoring in the dependency graph is deferred until the iterative proof-generation pipeline mostly succeeds.

-------

## Current State
The repo has working source-statement generation, archived provider-result capture, serial reusable-project Lean verification, shape diagnostics, and compiler-feedback repair queues. The strict hard six-row slice is now cumulatively 6/6 verified for `$0.21569744` after attempt-3 repairs recovered rows 2 (`fps_newtonBinomial_neg`) and 3 (`fps_comp_coeff_finite`). Serial Lean verification is not the bottleneck at this scale; prompt/repair quality is still the main scaling risk.

Key run directory: `docs/source-statement-runs/2026-05-05-strict-guidance-six-generation/`.
Main report: `docs/source-statement-strict-guidance-six-generation-report.md`.

## Active Goals
- [x] Push the strict hard six-row slice from 4/6 to 6/6 with cheap targeted repairs.
- [ ] Keep all paid OpenRouter results recoverable in git artifacts before Lean checking.
- [ ] Keep `STATUS.md` compact; use reports and git history for durable audit details.

## TODO Plan
- [ ] Use the recovered 6/6 slice as a seed for the next corpus-spread validation; do a zero-cost preflight before any larger paid run.
- [ ] Keep trust scoring deferred until larger slices mostly succeed.

## Blockers
- The overall textbook-scale pipeline is not ready for trust scoring; larger slices still fail too often.

## Recent Results
- Targeted guidance over the six remaining 11-row failures produced 0/6; strict guidance improved that to 2/6 first pass.
- Compiler/shape repairs recovered rows 6 and 5, bringing the strict hard slice to 4/6.
- Added repair-domain guidance for negative-binomial helper application and finite `finsum` support-subset failures; focused tests pass (`58 passed` for source-statement artifact/prompt tests).
- Regenerated shape diagnostics so row 3 no longer gets a false finite-composition warning; only the already-repaired row 5 group-power warning remains.
- Repair attempt 3 for rows 2 and 3 completed with 2/2 parsed outputs, 2 paid calls, `$0.012440043` actual cost, and both rows verified.

## Agent Notes
- Raw attempt-3 artifacts are committed in `529b9aa`; this checkpoint records the attempt-3 verification result and updated reports.
