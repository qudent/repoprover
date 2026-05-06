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
same-unit helper planning, Mathlib hydration, and clean
`cannot_prove_from_visible_context` handling on broader theorem units.

## Active Goals
- [ ] Use LaTeX statement units as the main planning and benchmark surface.
- [ ] Keep paid selector/generation outputs recoverable before verification.
- [ ] Select source text, previous book/source statements, previous project
  declarations, local file/import/style context, and Mathlib APIs separately.
- [ ] Make theorem-level semantic coverage and repair loops reliable on broader
  batches without benchmark leakage or theorem-specific hints.

## TODO Plan
- [x] Generate theorem-level source units and gold-candidate rows.
- [x] Add target-blind context selection, Mathlib hydration, generation,
  generated-only verification, gold comparison, semantic grading, and bounded
  repair loops.
- [x] Add visible-support materialization, same-unit helper planning, failure
  taxonomies, and context-gap diagnostics.
- [x] Fix NPartition API/context issues found so far: `Nat.Partition` fields,
  list/sort bridge hydration, `do_not_use_identifiers` sanitation, cardinality
  request rules, representation control, and unordered-data canonicalization.
- [x] Add generic composite-proof bridge notes for checked fallback facts such
  as `Multiset.sort_eq` + `Multiset.sum_coe`, then retry NPartition without
  theorem-specific prompt hints.
- [x] Add and evaluate a generic same-unit proof-planning stage for
  zero-padding monotonicity and inverse/`Equiv` helper structure.
- [ ] Decide how to enforce honest decline when the model can sketch helpers
  but cannot complete them without placeholders, or hand the helper skeleton to
  a coding agent/manual diagnostic lane.
- [ ] Reclassify old strict-grader mismatches into actionable buckets.
- [ ] Scale beyond determinant/symmetric probes and reduce noisy fallback
  context.

## Blockers
- Previous-project context is the strongest signal, but aligned target
  declarations for the selected source unit must remain hidden.
- Broad theorem units can require new same-unit helper definitions, not just a
  final theorem. `prop.sf.Npar-as-par` is the current hard case.
- Selectors/generators still miss Lean shapes: nonexistent Mathlib names,
  omitted binders/typeclasses, extensionality paths, proof APIs, and proof
  plans for fresh helpers.
- Full elaborated dependency extraction is useful but heavy on this 8 GB
  machine; reuse `docs/lean-elaborated-direct-deps.jsonl` unless a rerun is
  necessary. "Rows" there means one compiled Lean declaration/dependency record,
  not one LaTeX theorem unit.

## Recent Results
- Scale snapshot: 462 LaTeX source units, 114 gold-candidate units, and 414
  aligned Lean declarations; elaborated direct deps over gold units have median
  44 Mathlib and 5 project constants per unit.
- Proven positives: inverse uniqueness, determinant transpose, triangular
  determinant, mixed determinant batch, and symmetric `e_n = 0` can reach
  semantic coverage with target-blind context plus repair loops.
- Failure summary across 50 verification files / 71 unit checks: 16 compiled,
  21 old/new contract violations, 10 compile failures, and 24 clean cannot-prove
  declines. Deduplicated by source unit, 6/11 touched theorem units have
  compiled at least once.
- Context-gap diagnostics for 5 unresolved units: 3 missing Mathlib context, 1
  missing project context, and 1 same-source-intermediate case
  (`prop.sf.Npar-as-par`).
- NPartition retries progressively fixed generic issues: helper planning,
  `Nat.Partition` neighborhood hydration, list/sort bridge fallback,
  do-not-use sanitation, cardinality bridge requests, and representation
  control, and unordered-data canonicalization. Latest bridge hydration
  resolved guessed `Multiset.sum_sort` and `List.sum_of_sorted_antitone`
  requests to 13 checked signatures, 2 fallback-resolved requests, and 0
  failed/unchecked requests.
- Bridge-note context now adds 2 generic fallback composition notes over the 13
  checked signatures, with 0 failed/unchecked context requests. Latest paid
  NPartition retry cost `$0.00355558`; it still cleanly declined with gold
  comparison `not_generated_cannot_prove`.
- Zero-padding planner retry cost `$0.00436282`, hydrated 19 checked signatures
  with 0 failed requests, and fixed the guessed `Multiset.card_filter_le` shape
  to `Multiset.filter_le` + `Multiset.card_le_card`. Repair cost `$0.00398090`
  and generated the intended helper skeleton, but with `sorry`, comments, and
  ellipses, so verification is `contract_violation`.
- Current NPartition blocker: generation discipline/proof synthesis. The model
  can now sketch the right helper structure, but cannot complete the hard
  same-unit proofs honestly under the no-placeholder benchmark contract.
- Test suite last passed: `uv run pytest tests` (`476 passed`) plus
  `py_compile` over selector/generator/repair/verifier scripts. Full
  `uv run pytest` still has one unrelated blueprint fixture failure because
  `../docbuild/.lake/build/doc/declarations/declaration-data.bmp` is absent.

## Agent Notes
- Current `main` is ahead of `origin/main`; do not assume remote is current.
- Do not kill existing Lean/lake checks. Monitor passively and let them finish.
- A separate CauchyBinet diagnostic Codex/Lean task is running; leave it alone.
- Next useful work: either add a stricter repair contract that converts
  placeholder skeletons back to `cannot_prove_from_visible_context`, or route
  the checked helper skeleton to a coding-agent/manual diagnostic lane.
