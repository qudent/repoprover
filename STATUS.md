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
`docs/latex-statement-gold-candidates.jsonl`. Current work is on target-hidden
context acquisition, model ablations, proof-lane repair, and verifier speed.

## Active Goals
- [ ] Keep LaTeX statement units as the benchmark surface.
- [ ] Keep every paid selector/generation/repair output recoverable and logged.
- [ ] Select source/project/local/Mathlib context without hidden target leakage.
- [ ] Route failures by class before changing prompts or retrying models.
- [ ] Determine whether a cheap 90%+ book formalization path is plausible.

## TODO Plan
- [x] Add theorem-level source units and gold-candidate rows.
- [x] Add selector, hydrator, generator, verifier, semantic grader, repair loop,
  proof-lane tasks, failure summaries, and run ledger.
- [x] Add report/workflow guardrails in `AGENTS.md`: fixed panels, model
  ablations, budget gates, ledgers, and stop/reroute rules.
- [x] Try stronger model probes with realistic Lean timeouts.
- [x] Measure and reduce verifier Lean-call overhead.
- [x] Add bounded same-file dependency closure for visible prior project
  declarations.
- [ ] Build the next non-dev fresh panel from the current fixed pipeline and
  judge context selection/proof synthesis separately.

## Blockers
- Current evidence does not justify a `$100`/90% book-formalization claim.
  Fresh-slice honest proof-lane scores are still weak.
- Previous-project context helps more than pure Mathlib lookup, but aligned
  target declarations must stay hidden.
- Selectors still invent or miss APIs; hydration catches many gaps but proof
  synthesis still fails on some real Lean proof shapes.
- Lean verification is still slow because checks repeatedly start
  `lake env lean --stdin --json`; batching reduced this but did not remove the
  import/startup cost.
- One-off hard-theorem retries are a known antipattern; use frozen panels and
  ledger rows for new claims.

## Recent Results
- Scale snapshot: 462 LaTeX source units, 114 gold-candidate units, 414 aligned
  Lean declarations. Elaborated gold-unit deps have median 44 Mathlib and 5
  project constants per unit.
- Honest open-model proof-lane full-panel reruns after hidden-target and support
  checks scored `0/5` semantic for both DeepSeek V4 Pro no-reasoning and Kimi
  K2.6 no-reasoning.
- DeepSeek V4 Pro high-reasoning/32k on units 002+004 cost `$0.018949238` and
  reached `1/2` compile plus `1/2` semantic; Kimi K2.6 high-reasoning returned
  reasoning-only/null content on one unit and hung on the next.
- Verifier timing improved on the DeepSeek-high two-unit artifact from 28 Lean
  calls / 367.128s to 10 calls / 154.669s after batching support materialization
  and inferred-open validation.
- Failure overview now shows no current no-sorry/placeholder contract failures;
  current failures are clean declines, missing API/context, ill-typed generated
  terms, proof-tactic shape, or timeouts.
- Latest targeted unit004 paid diagnostic fixed a generic context gap:
  `allEvenTuples` is now included as a dependency of selected visible
  `allEven_count_formula` context. The rerun accepted all 11 support assumptions
  but still failed on proof shape (`rw [signSum, ..., signProduct]`).
- The interrupted unit004 repair attempt is logged as a paid repair-context
  selection row; repair generation did not complete before the user redirected.

## Agent Notes
- Current `main` is far ahead of `origin/main`; do not assume remote is current.
- Do not kill existing Lean/lake/Codex checks unless explicitly asked.
- Latest Codex-log audit used the current rollout JSONL:
  `/home/name/.codex/sessions/2026/05/04/rollout-2026-05-04T23-33-24-019df556-de1a-7422-9dde-2d68226a1c96.jsonl`.
- Next useful work: a fresh fixed-panel run with the current context/dependency
  logic, followed by routed failure analysis before any new prompt tuning.
