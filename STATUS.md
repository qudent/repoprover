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
- [ ] Validate whether the pipeline can plausibly reach cheap 90%+ book
  formalization; current evidence is not sufficient for a `$100`/90% claim.

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
- [x] Run a fixed model/context ablation on the same theorem-level panel:
  DeepSeek V4 Flash vs DeepSeek V4 Pro vs Kimi K2.6 vs GPT-5.5, with identical
  hidden-target context packs and acceptance metrics.
- [ ] Keep a run ledger row for each paid or acceptance-bearing theorem-level
  run.

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
- History review shows a recurring mistake: turning one hard theorem's failure
  into prompt/context rules and retesting the same theorem. The fix is now
  encoded in `AGENTS.md`: use panels, ledgers, and model ablations before more
  one-off retries.
- Full elaborated dependency extraction is useful but heavy on this 8 GB
  machine; reuse `docs/lean-elaborated-direct-deps.jsonl` unless a rerun is
  necessary.
- One-unit model probes need verifier timeouts above the import-stack baseline:
  the same proof attempts that timed out at 120s compiled at 360s.
- Lean verification is still slower than desired because each validation/final
  batch starts a fresh `lake env lean --stdin --json`; measured cold
  `import Mathlib` was about 25s and a warmed project-import check about 15s.
  Inferred-open and support materialization checks are now batched, which
  removes the worst per-item loops.

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
- Bottom-line viability: current artifacts show cheap recoverable pipeline
  components, but not a robust `$100`/90% book-formalization path. Fresh-slice
  proof-lane acceptance is still `0/5`, so proof synthesis/context routing must
  improve substantially before scaling claims are credible.
- Implemented report recommendations in local workflow: `AGENTS.md` now requires
  history checks, frozen panels, model ablations, budget gates, run ledgers, and
  stop/reroute rules; the ablation config/command builder and ledger writer are
  under `configs/` and `scripts/`.
- Older one-unit proof-lane probes need to be read cautiously unless rerun with
  selector-derived hidden-target filtering and checked support assumptions. GPT
  and DeepSeek high reasoning can solve the easy FPS unit; hard unit 004 still
  fails despite stronger proof attempts.
- Benchmark honesty correction: proof-lane runs now inherit the selector path
  from `proof-lane-summary.json`, so target-module imports are filtered. After
  this and support-assumption checking, full fresh-slice open-model proof-lane
  scores are honest `0/5` compile/semantic for both DeepSeek V4 Pro
  no-reasoning (`$0.016758781`) and Kimi K2.6 no-reasoning (`$0.10070847`,
  including the logged truncated retry).
- DeepSeek V4 Pro high-reasoning/32k on units 002+004 cost `$0.018949238` and
  used 16,293 reasoning tokens. It reached `1/2` compile and `1/2` semantic:
  unit 002 FPS passed the hidden gold grader; unit 004 still failed on concrete
  Lean proof/API errors (`Fin.snoc_injective`, sum-product rewrite, heartbeat).
- Kimi K2.6 high-reasoning/32k is not usable through the tested OpenRouter route
  as-is: unit 002 returned 10,264 reasoning tokens, null assistant content, no
  JSON, cost `$0.05606217`; unit 004 was interrupted after >35 min with no
  response. See the interruption audit in the run artifact.
- Added verifier timing/counter instrumentation and a reusable failure overview
  script. Initial timed DeepSeek-high two-unit verifier rerun used 28 Lean calls
  and 367.128s cumulative Lean elapsed, with support checks alone at 22 calls
  and 258.225s. Batching support plus inferred-open validation kept the result
  at `1/2` compile/semantic but reduced verification to 10 Lean calls and
  154.669s; support work is now 6 calls and 72.65s, and inferred-open
  validation is 2 calls. Current overview is
  `reports/latex-statement-failure-overview-20260506T1740Z.md`.
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
- Next useful work: reuse a warmed Lean process if practical, then route the
  remaining failures by class. Current failures are mostly clean declines or
  real proof/API errors, not no-sorry contract violations.
