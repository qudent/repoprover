# RepoProver - Status
## Overall Direction
Build a cheap, reproducible source-LaTeX-to-Lean autoformalization pipeline for
Algebraic Combinatorics. The production unit is one LaTeX theorem/environment,
planned into one or more Lean declarations with selected source/project/local
and Mathlib context, then checked by Lean plus post-hoc semantic coverage.

-------

## Current State
The repo has pivoted from declaration-level rows to theorem-level LaTeX
statement rows. Main datasets are `docs/latex-statement-units.jsonl` and
`docs/latex-statement-gold-candidates.jsonl`; old declaration-level artifacts
are preserved at `checkpoint/before-per-latex-statement-dataset`. Current work
is testing target-blind context selection, visible-support materialization,
same-unit helper planning, and honest `cannot_prove_from_visible_context`
handling on broader theorem units.

## Active Goals
- [ ] Use LaTeX statement units as the main planning and benchmark surface.
- [ ] Keep paid selector/generation outputs recoverable before verification.
- [ ] Select source text, previous book/source statements, previous project
  declarations, local file/import/style context, and Mathlib APIs separately.
- [ ] Make theorem-level semantic coverage and repair loops reliable on broader
  batches without benchmark leakage or theorem-specific hints.

## TODO Plan
- [x] Generate theorem-level source units and gold-candidate rows.
- [x] Add Lean-tooling hydration for selector-requested and fallback Mathlib names.
- [x] Add theorem-level generation, generated-only verification, exact-name
  comparison, semantic coverage grading, and bounded repair loops.
- [x] Add target-blind local predecessor/dependency context and visible-support
  materialization.
- [x] Preserve raw model text and normalize invalid `cannot_prove` outputs
  before downstream verification.
- [x] Add failure taxonomies and context-gap diagnostics.
- [x] Add generic same-unit helper planning with `role` and `depends_on_task_ids`.
- [ ] Reclassify old strict-grader mismatches into actionable buckets.
- [ ] Scale beyond determinant/symmetric probes and reduce noisy fallback context.
- [x] Test helper planning plus better Mathlib/project context on
  `prop.sf.Npar-as-par` without exposing same-source gold declarations.
- [x] Turn the remaining NPartition failure into a precise missing-proof-context
  report.
- [x] Add a source-only proof-planning/helper-synthesis contract for same-unit
  lemmas.
- [x] Run a paid helper-plan repair-context retry and generation repair on
  NPartition.
- [x] Improve NPartition fallback hydration enough to select checked list/sort
  bridge facts for stale `List.Sorted` requests.
- [ ] Resolve the remaining NPartition blocker by synthesizing the padded
  construction/length-bound helper proof or switching away from sorted-list
  indexing.

## Blockers
- Previous-project context is the strongest signal, but aligned target
  declarations for the selected source unit must remain hidden.
- Broad theorem units can require new same-unit helper definitions, not just a
  final theorem. `prop.sf.Npar-as-par` currently needs this.
- Selectors/generators still miss Lean shapes: nonexistent Mathlib names,
  omitted binders/typeclasses, extensionality paths, or proof APIs.
- Full elaborated dependency extraction is useful but heavy on this 8 GB
  machine; reuse `docs/lean-elaborated-direct-deps.jsonl` unless a rerun is
  necessary.

## Recent Results
- Scale snapshot: 462 LaTeX source units, 114 gold-candidate units, and 414
  aligned Lean declarations; elaborated direct deps over gold units have median
  44 Mathlib and 5 project constants per unit.
- Proven positives: inverse uniqueness, determinant transpose, triangular
  determinant, mixed determinant batch, and symmetric `e_n = 0` can reach
  semantic coverage with target-blind context plus repair loops.
- Diverse4 remains the negative frontier: after transport fixes, split
  generation, visible-support materialization, and two repair rounds, coverage
  stayed `0/4`; the blocker is missing useful project/Mathlib proof context.
- Failure summary across 40 verification files / 61 unit checks: 16 compiled,
  20 old contract violations, 10 compile failures, and 15 clean cannot-prove
  declines. Deduplicated by source unit, 6/11 touched theorem units have
  compiled at least once.
- Context-gap diagnostics for 5 unresolved units: 3 missing Mathlib context, 1
  missing project context, and 1 same-source-intermediate case
  (`prop.sf.Npar-as-par`).
- Paid NPartition helper-contract v1 cost `$0.00360500` total
  (`$0.00097524` selection, `$0.00262976` generation). The selector planned two
  `same_unit_helper` defs plus one dependent `main_claim`; hydration rejected
  guessed `Nat.Partition.length`; generation again raw-emitted helper-shaped
  Lean while reporting `cannot_prove_from_visible_context`. The runner
  normalized it to an empty output, verification classified
  `declined_cannot_prove`, and gold comparison classified
  `not_generated_cannot_prove`.
- Generic Mathlib type-neighborhood hydration now adds compact checked
  structure/class source plus checked projection/extensionality neighbors. For
  `Nat.Partition` it adds `parts`, `parts_pos`, `parts_sum`, `ext`, and
  `ext_iff`, suppresses eight unrelated `Nat.*length*` fallbacks, and shrinks
  the NPartition prompt from 78,802 to 60,942 bytes. Paid retry cost
  `$0.00206416`; raw output correctly used `Multiset.card p.parts` instead of
  nonexistent `Nat.Partition.length`, but still normalized to a clean
  `declined_cannot_prove`.
- NPartition repair-context loop cost `$0.00681880` and selected 9 checked
  signatures around `Multiset.card`, `Multiset.sort`, `Multiset.sort_sorted`,
  `List.get`, `Multiset.length_sort`, and `Nat.Partition.ext`. It still
  cleanly declined, diagnosing missing same-unit inverse/padding proof lemmas.
  A filtered repair retry cost `$0.00294070`; after fallback search stopped
  matching universe `Sort` for `sort`, it also declined. This is now a precise
  missing-proof-context/helper-synthesis blocker, not a `Nat.Partition.length`
  API hallucination.
- Repair-context selection now has a `same_unit_helper_plan` schema for fresh
  helper definitions/lemmas/theorems, and repair generation is instructed to
  introduce those helpers before the main declaration when checked context
  supports them. No-cost NPartition prompt artifact:
  `docs/latex-statement-repair-loop-runs/2026-05-06-npartition-helper-plan-budget/`.
- Paid helper-plan loop cost `$0.00638078`. The selector proposed
  `partitionLength`, `fromPartition'`, `toNPartition'`, and an `Equiv` theorem
  as fresh same-unit helpers and hydrated 17 checked signatures. Repair still
  declined because `List.Sorted.rel_of_lt` was unavailable and the proof that
  visible `toPartition` has length at most `N` is still missing.
- Bridge-hydration retry now uses signature shapes, Lean diagnostics, and
  simple Mathlib aliases in fallback search. It hydrates 18 checked signatures,
  including `List.Sorted.rel_get_of_lt`, `List.Sorted.rel_get_of_le`,
  `List.Pairwise.rel_get_of_lt`, and `List.Pairwise.rel_get_of_le`. Paid repair
  retry cost `$0.00357280` and still cleanly declined, so the remaining blocker
  is proof synthesis for the padded construction, `toPartition` length bound,
  and inverse proofs rather than missing list/sort bridge API context.
- Focused theorem-level suite last passed: 84 pytest tests plus `py_compile`
  over selector/generator/repair/verifier scripts.

## Agent Notes
- Current `main` is ahead of `origin/main`; do not assume remote is current.
- Do not kill existing Lean/lake checks. Monitor passively and let them finish.
- A separate CauchyBinet diagnostic Codex/Lean task is running; leave it alone.
- Next useful work: make the helper planner produce/prove a concrete
  `toPartition` cardinality bound and inverse lemmas from visible same-unit
  context, or choose a construction that avoids sorted-list indexing.
