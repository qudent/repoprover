# RepoProver - Status
## Overall direction
Build a cheap, reproducible source-to-Lean autoformalization pipeline for the Algebraic Combinatorics dataset: honest source/prefix context, recoverable provider outputs, reusable Lean verification, and failure-driven context/repair iteration. Trust scoring is deferred until realistic source-only slices mostly succeed.

-------

## Current State
The strict 6-row hard slice reached 6/6, but that used target-comment context and is debugging evidence only. Current validation is source-only with a separate LLM selector for source-part choice, previous project statements, and tight Mathlib/API context before generation. Project-context proof generation now has two realistic passes across two domains, but not yet enough diverse coverage to call the pipeline reliable.

## Active Goals
- [ ] Keep every paid OpenRouter output recoverable in git before Lean checking.
- [ ] Improve realistic context selection, especially source-part disambiguation and Mathlib API selection, before larger generation runs.
- [ ] Expand selector-selected previous project context plus Mathlib context from the current 1-pass proof to a small diverse slice.
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
- [x] Apply the project-context selector output and run generation/verification after committing paid selector artifacts.
- [x] Run a small diverse project-context generation/verification probe.
- [x] Tighten selector behavior for shared TeX labels where the target is the next declaration-level formalization, not the whole labeled theorem.
- [x] Re-run a small paid selector/generation probe after the declaration-progress prompt fix.
- [x] Document pipeline neuralgic points, prompt contracts, and corpus/Mathlib scale.
- [ ] Verify the latest declaration-progress generation outputs in Lean.
- [ ] Shrink selector schema so 4-record batches complete as valid JSON.

## Blockers
- Source-only context still often lacks exact theorem-family cues: target-comment focus terms are absent from visible source spans in `45/64` broader audit rows.
- The deterministic gold-candidate source spans are usually broad: `62/64` broad, `61/64` multi-environment, `60/64` extra-label rows in the latest audit.
- `det_minors_diag` still fails: the model invents unavailable Cauchy-Binet helper names and produces malformed proof syntax. Treat it as a harder repair/context case, not evidence that project-context selection failed.
- Shared TeX labels remain a live failure mode: in the diverse3 run, the selector correctly found useful previous-project facts for `prod-lim-conv`, but told the generator to bundle the prior multipliability result with the target equality theorem, so the hidden grader rejected the generated theorem shape.
- Broad theorem labels can still hide narrow targets: the Laurent `T_inv` row became an over-broad `laupol_ring` statement and did not compile.
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
- Project-context generation run `2026-05-05-project-context-selected-generation-paid` cost `$0.022922122`; after grader fixes, verification passed `1/2`, with `alternant_swap_of_ne` proving the withheld `alternant_swap` target.
- Diverse project-context selector run `2026-05-05-context-selection-project-context-diverse3-paid` cost `$0.004148956`; generation run `2026-05-05-project-context-diverse3-generation-paid` cost `$0.021010413`; verification passed `1/3` with `isInverse_unique` proving via imported `inverse_unique`.
- Declaration-progress prompt fix adds `same_label_progress_summary` and `supporting_context_boundary`; zero-cost diverse3 audit `2026-05-05-context-selection-decl-progress-diverse3-budget` made `0` paid calls and kept target-name leaks at `0`.
- Paid declaration-progress selector `2026-05-05-context-selection-decl-progress-diverse3-paid` cost `$0.00558124`; it selected the narrow equality for `prod-lim-conv` and marked multipliability as support-only. Follow-up generation-only `2026-05-05-decl-progress-diverse3-generation-paid` returned `3/3` outputs for `$0.019770489`; not Lean-verified yet.
- Report `docs/context-selection-pipeline-report-2026-05-05.md` explains why one LaTeX theorem should be the planning unit, while Lean declarations remain inner-loop verification units. `README.md` now records corpus and Mathlib scale estimates.
- Focused tests pass with source-statement, source-context-selection, context graph, and materializer tests.

## Agent Notes
- Useful proof paths so far are previous-project theorem reuse: `alternant_swap` via imported `AlgebraicCombinatorics.alternant_swap`, and `isInverse_unique` via imported `inverse_unique`.
- Next work should verify the latest generated declarations. The first two generated shapes look improved; Laurent still bundles unity and invertibility and likely remains a source-unit mismatch.
