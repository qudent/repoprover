# RepoProver - Status
## Overall direction
Build a cheap, reproducible source-to-Lean autoformalization pipeline for the Algebraic Combinatorics dataset: honest source/prefix context, recoverable provider outputs, reusable Lean verification, and failure-driven context/repair iteration. Trust scoring is deferred until realistic source-only slices mostly succeed.

-------

## Current State
The strict 6-row hard slice reached 6/6, but that used target-comment context and is debugging evidence only. Current validation is source-only with a separate LLM selector for source-part choice, previous project statements, and tight Mathlib/API context before generation.

## Active Goals
- [ ] Keep every paid OpenRouter output recoverable in git before Lean checking.
- [ ] Improve realistic context selection, especially source-part disambiguation and Mathlib API selection, before larger generation runs.
- [ ] Prove that selector-selected previous project context plus Mathlib context improves generation/repair success on a small diverse slice.
- [ ] Use broader source-only slices as the main evidence, not the old six-row loop.

## TODO Plan
- [x] Add source-only prompt mode and TeX-derived focus.
- [x] Run and repair an 11-record source-only validation slice.
- [x] Add TeX environment-balance span expansion.
- [x] Add same-file source-label local API retrieval.
- [x] Run a zero-cost 64-record source-only context audit.
- [x] Run paid generation-only on an 8-record easier source-only subset from the 64-row audit.
- [x] Commit raw easy-8 paid outputs before Lean verification.
- [x] Verify easy-8 generated outputs serially.
- [x] Triage easy-8 failures before another paid run.
- [x] Add LLM context-selection runner with Mathlib hydration and post-hoc gold comparison.
- [x] Probe Kimi K2.6, DeepSeek V4 Flash, and Gemini Flash selector behavior with logged paid artifacts.
- [x] Apply successful selector output to context-enhanced records and run a small generation/verification probe.
- [x] Add source-part disambiguation before generation to avoid broad `(a)/(b)` conjunction outputs.
- [x] Add imported previous-project source-label context candidates to selector payloads.
- [ ] Apply the project-context selector output and run generation/verification after committing paid selector artifacts.
- [ ] Shrink selector schema so 4-record batches complete as valid JSON.

## Blockers
- Source-only context still often lacks exact theorem-family cues: target-comment focus terms are absent from visible source spans in `45/64` broader audit rows.
- The deterministic gold-candidate source spans are usually broad: `62/64` broad, `61/64` multi-environment, `60/64` extra-label rows in the latest audit.
- Existing generated proofs still fail Lean on the latest two-record source-progress run: `det_minors_diag` invents unavailable helper names; `alternant_swap` needed previous-project context and explicit type arguments.
- A 72-record preflight was too slow with current Lean setup; keep validation slices bounded until verification reuse is improved.

## Recent Results
- Source-only 11-row generation plus compile repair reached `4/11` for about `$0.153232781`.
- Balanced-span rerun cost `$0.126677307`, still `1/11`; shape repairs cost `$0.020500999` and did not add passes.
- Latest 64-row budget audit made zero paid calls, estimates max generation cost at `$1.976172810`, has `0` hidden target-name payload hits, and extracts focused labeled environments for `64/64` rows.
- Easy-8 source-only generation made `8/8` paid calls, cost `$0.071505155`, and verified `1/8` after materialization fixes.
- Context-selection pilot report: `docs/source-context-selection-pilot-2026-05-05.md`.
- Best selector probe was `deepseek/deepseek-v4-flash` without reasoning on 2 records: valid JSON, Mathlib hydration, `$0.0025886`, zero payload target-name leaks.
- Kimi K2.6 and reasoning-mode Flash probes mostly spent tokens on hidden reasoning and returned no usable JSON; current selector batch size should be 2, not 4.
- Context-selected generation probe cost `$0.02031073` for one returned output; verification passed `0/2`.
- Source-progress selector plus generation fixed the semantic over-bundling for `alternant_swap`, but verification stayed `0/2`; a generic `noncomputable section` materialization fix removed the first alternant compiler blocker.
- New project-context selector run `2026-05-05-context-selection-project-context-paid` cost `$0.002581152`; `alternant_swap` selected part (b) and identified imported `AlgebraicCombinatorics.SymmetricFunctions.LittlewoodRichardson.alternant_swap` as the direct proof route.
- Focused tests pass with source-statement, source-context-selection, context graph, and materializer tests.

## Agent Notes
- Commit the project-context selector artifacts before applying them to a new generation/verification run.
- Next generation should prefer selector-selected previous project context; for `alternant_swap`, the desired proof shape is `simpa [alternant] using AlgebraicCombinatorics.alternant_swap hij`.
