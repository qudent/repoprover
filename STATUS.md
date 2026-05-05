# RepoProver - Status
## Overall direction
Build a cheap, reproducible autoformalization pipeline for the Algebraic Combinatorics gold-standard dataset: select honest source/prefix context, generate Lean statements/proofs without exposing withheld targets, preserve all provider outputs, verify in reusable Lean projects, and iterate from concrete failures. Trust scoring in the dependency graph is deferred until the iterative proof-generation pipeline mostly succeeds.

-------

## Current State
The repo has working source-statement generation, archived provider-result capture, serial reusable-project Lean verification, shape diagnostics, and compiler-feedback repair queues. The best strict hard six-row slice is 4/6 verified for `$0.203257397` before repair attempt 3; rows 2 (`fps_newtonBinomial_neg`) and 3 (`fps_comp_coeff_finite`) now have parsed attempt-3 repair outputs awaiting Lean verification. Serial Lean verification is not the bottleneck at this scale; prompt/repair quality is.

Key run directory: `docs/source-statement-runs/2026-05-05-strict-guidance-six-generation/`.
Main report: `docs/source-statement-strict-guidance-six-generation-report.md`.

## Active Goals
- [ ] Push the strict hard six-row slice from 4/6 toward 6/6 with cheap targeted repairs.
- [ ] Keep all paid OpenRouter results recoverable in git artifacts before Lean checking.
- [ ] Keep `STATUS.md` compact; use reports and git history for durable audit details.

## TODO Plan
- [ ] Commit raw repair attempt 3 artifacts before verification.
- [ ] Verify any parsed attempt-3 repair outputs with `scripts/verify_source_statement_generation.py`.
- [ ] Update the strict-guidance report with attempt-3 generation/verification results.
- [ ] If rows 2/3 still fail, do more zero-cost prompt/diagnostic work before additional paid calls.

## Blockers
- The overall textbook-scale pipeline is not ready for trust scoring; larger slices still fail too often.

## Recent Results
- Targeted guidance over the six remaining 11-row failures produced 0/6; strict guidance improved that to 2/6 first pass.
- Compiler/shape repairs recovered rows 6 and 5, bringing the strict hard slice to 4/6.
- Added repair-domain guidance for negative-binomial helper application and finite `finsum` support-subset failures; focused tests pass (`58 passed` for source-statement artifact/prompt tests).
- Regenerated shape diagnostics so row 3 no longer gets a false finite-composition warning; only the already-repaired row 5 group-power warning remains.
- Repair attempt 3 for rows 2 and 3 completed with 2/2 parsed outputs, 2 paid calls, and `$0.012440043` actual cost.

## Agent Notes
- Attempt 3 generated plausible row 2 and row 3 repairs; commit the raw artifacts first, then verify with the reusable-project verifier.
