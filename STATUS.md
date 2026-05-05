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
- [x] Rerun theorem-level selection after the new "prose sketch only" selector
  contract, then retry generation on an easier source unit.
- [x] Add a post-hoc theorem-level gold-name comparison that distinguishes
  compile success from oracle coverage.
- [x] Add a post-hoc theorem-level semantic coverage check using grader-only
  gold statements and the existing `simpa using` criterion.
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
  but it must not leak exact target declarations. The selector now pulls safe
  prior project declarations from the full source-unit index, including
  source-only rows' `referencing_lean_declarations`, but this needs more
  sampling before it can be trusted as complete.
- The old declaration-level verifier can reject useful source-theorem progress
  when the generated declaration sequence does not match one hidden Lean row.
- The inverse-uniqueness theorem-level attempt now compiles, but the generated
  declaration is an alternate explicit-hypothesis theorem named
  `inverse_unique`; exact post-hoc gold-name overlap with
  `AlgebraicCombinatorics.FPS.isInverse_unique` is `0/1`. This is source-level
  progress requiring semantic review, not gold coverage. The new semantic
  grader also reports `0/1` and classifies the failure as
  `shape_mismatch_against_oracle`: the generated theorem requires symmetric
  multiplication hypotheses that the gold `IsInverse` statement does not have
  directly.
- A v3 rerun with prior project context fixes that specific shape issue and
  reaches semantic coverage `1/1`, but generated-only verification currently
  needs explicit project imports/opens to see names such as `IsInverse`.
  Automating that verification context is still open.
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
- Second theorem-level context/generation probe:
  `docs/latex-statement-context-runs/2026-05-05-inverse-unique-source-context-v2-paid/`
  selected prior source context plus `CommRing`, `mul_assoc`, `one_mul`, and
  `mul_one`; hydration checked `4/4` exact identifiers. Generation in
  `docs/latex-statement-generation-runs/2026-05-05-inverse-unique-deepseek-v4-flash-paid/`
  compiled `1/1`, with post-hoc exact gold-name comparison `0/1` and semantic
  grader coverage `0/1`.
- New script `scripts/verify_latex_statement_semantic_coverage.py` materializes
  grader-only aligned-gold checks after generation. The inverse artifact is
  `docs/latex-statement-generation-runs/2026-05-05-inverse-unique-deepseek-v4-flash-paid/eval/semantic-coverage.json`.
- Selector payloads now include prior project declarations from full source
  units, not only gold-candidate rows. Budget-only proof:
  `docs/latex-statement-context-runs/2026-05-05-inverse-unique-prior-project-v3-budget/`
  includes prior `IsInverse`/`IsInvertible` snippets from
  `def.commring.inverse` and still hides the target `isInverse_unique`
  alignment.
- Paid v3 inverse rerun:
  `docs/latex-statement-context-runs/2026-05-05-inverse-unique-prior-project-v3-paid/`
  cost `$0.00038332`, valid JSON, `0` reasoning tokens, selected
  `AlgebraicCombinatorics.FPS.IsInverse`; hydration checked `mul_comm` and
  rejected `mul_left_cancel₀` as not an exact identifier. Generation in
  `docs/latex-statement-generation-runs/2026-05-05-inverse-unique-prior-project-v3-paid/`
  cost `$0.0004417`, emitted `IsInverse.unique`, compiled `1/1` with project
  imports/opens, exact name overlap `0/1`, semantic coverage `1/1`.

## Agent Notes
- Current `main` is ahead of `origin/main`; do not assume remote is current.
- No Lean scan is currently running. Reuse the checked-in scan JSONL for new
  summaries.
- Do not kill existing Lean/lake checks. If one is running, monitor it
  passively and let it finish.
- Focused Python tests should cover the dataset generator, theorem selector
  payload hiding, context hydration, theorem generation payloads, verifier
  classification, context graph generation, and elaborated dependency summary.
