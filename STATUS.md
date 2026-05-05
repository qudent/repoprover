# RepoProver - Status
## Overall Direction
Build a cheap, reproducible source-to-Lean autoformalization pipeline for the
Algebraic Combinatorics dataset. The current production unit is one LaTeX
theorem/environment as a planning work item, decomposed into Lean declaration
tasks with selected source/project/local/Mathlib context and honest
post-hoc verification.

-------

## Current State
The repo has pivoted from declaration-level "minimal-context" rows to
theorem-level LaTeX statement rows. The old canonical declaration-level JSON
dataset is checkpointed at `checkpoint/before-per-latex-statement-dataset` and
retired from `main`; historical run logs remain. The current dataset is
`docs/latex-statement-units.jsonl` plus
`docs/latex-statement-gold-candidates.jsonl`.

## Active Goals
- [ ] Use LaTeX statement units as the main benchmark/planning surface.
- [ ] Keep paid selector/generation outputs recoverable before verification.
- [ ] Select context in separate buckets: source text, previous book/source
  statements, previous project declarations, local file/import/style context,
  and Mathlib APIs.
- [ ] Move from declaration-level pass/fail toward theorem-level coverage with
  inner-loop Lean declaration checks.

## TODO Plan
- [x] Add Lean-tooling context hydration for selector-requested Mathlib names
  (`#check`/environment lookup before generation).
- [x] Generate and verify one small theorem-level attempt from a planned LaTeX
  source unit.
- [ ] Rerun theorem-level selection after the new "prose sketch only" selector
  contract, then retry generation on an easier source unit.
- [ ] Reclassify old strict-grader mismatches into `compile_failure`,
  `missing_context`, `wrong_math`, `shape_mismatch_against_oracle`, or
  `useful_alternative_formalization`.
- [ ] Compact the theorem-level selector schema before trying batch size > 1.

## Blockers
- The first theorem-level selector smoke understood the FPS division-congruence
  lemma, but its unchecked Lean-like statement sketch used wrong API argument
  order. Future selector sketches must stay prose/math-intent only.
- The first theorem-level generation attempts reached valid JSON but `0/1`
  compile pass. V1 burned tokens on hidden reasoning until `reasoning_effort`
  was forced to `none`; v2 still copied `coeff K m` and emitted an incomplete
  theorem body despite reporting `cannot_prove_from_visible_context`.
- Previous-project context has been more useful than pure Mathlib lookup so far,
  but it must not leak exact target declarations.
- The old declaration-level verifier can reject useful source-theorem progress
  when the generated declaration sequence does not match one hidden Lean row.
- Full Lean dependency extraction is feasible but heavy on this 8 GB machine;
  reuse `docs/lean-elaborated-direct-deps.jsonl` instead of rerunning Lean
  unless needed.

## Recent Results
- Checkpoint before pivot: branch/tag
  `checkpoint/before-per-latex-statement-dataset` /
  `checkpoint-before-per-latex-statement-dataset` at `2c21627`.
- New LaTeX statement dataset: 462 source units, 114 gold-candidate units, 414
  aligned Lean declarations, median 2 declarations per gold unit, p90 8, max 29.
- First theorem-level selector run:
  `docs/latex-statement-context-runs/2026-05-05-deepseek-v4-flash-paid/`;
  valid JSON, 1 unit, `$0.00073584`, one planned declaration task with separate
  source/project/Mathlib context buckets.
- Lean-signature hydration for that selector output checked 4/4 exact Mathlib
  identifiers with `lake env lean --stdin --json`; artifacts are in
  `batch-001/mathlib-lean-hydrated-context.json`.
- Theorem-level generation runner and verifier now exist. No-reasoning DeepSeek
  generation cost `$0.0005976` for v1 and `$0.00045612` for v2; both verified
  `0/1` compile pass. The verifier records placeholders, contract violations,
  and Lean errors under each generation run's `eval/verification-results.json`.
- Lean-tooling dependency scan finished without being killed: 16,485 unique raw
  project constant rows. The theorem-level summary over 114 units sees median
  44 direct Mathlib constants and median 5 direct project constants per unit.
- README and `docs/context-selection-pipeline-report-2026-05-05.md` now record
  the scale numbers, prompt contracts, theorem-level plan, and benchmark
  honesty caveats.

## Agent Notes
- Current `main` is ahead of `origin/main`; do not assume remote is current.
- No Lean scan is currently running. Reuse the checked-in scan JSONL for new
  summaries.
- Focused Python tests should cover the dataset generator, theorem selector
  payload hiding, context hydration, theorem generation payloads, verifier
  classification, context graph generation, and elaborated dependency summary.
