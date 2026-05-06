# Five-Unit LaTeX Statement Dev Panel

Generated: `2026-05-06T06:12Z`

This is a development panel, not a held-out benchmark. The panel definition is
`docs/latex-statement-dev-panel-2026-05-06.json`.

## Why This Panel Exists

Optimizing on one LaTeX theorem is not a good training-loop signal. A single
unit is useful as a canary or root-cause probe, but it cannot distinguish:

- easy positive-control regressions;
- project-context retrieval failures;
- Mathlib API name recall failures;
- proof-planning failures after context is already checked;
- hard same-unit helper synthesis failures.

The fixed five-unit panel mixes those cases:

| Unit | Role | Contamination |
|---|---|---|
| `thm.commring.inverse-uni` | known positive / project-context control | dev known positive |
| `thm.det.triang` | known positive / Mathlib-local-style control | dev known positive |
| `lem.fps.prod.irlv.cong-div` | unresolved project/FPS context gap | dev gap case |
| `prop.binom.vandermonde.NN` | Mathlib bridge plus proof-planning case | dev contaminated by Vandermonde hydration work |
| `prop.sf.Npar-as-par` | hard same-unit helper-planning case | dev contaminated by NPartition iterations |

## Runs

### Budget Payload

Artifact:
`docs/latex-statement-context-runs/2026-05-06-dev-panel5-v1-budget/`

- Paid call: no.
- Units selected: 5.
- Prompt payload: 72,421 bytes.
- Model-facing user message: 66,958 characters.
- Hidden aligned target declaration names were not found in the payload by a
  direct string scan of the known post-hoc aligned names.

### Default Reasoning Selector

Artifact:
`docs/latex-statement-context-runs/2026-05-06-dev-panel5-v1-paid/`

- Model: `deepseek/deepseek-v4-flash`.
- Valid JSON: yes.
- Elapsed: 115.186 seconds.
- Cost: `$0.003094084`.
- Usage: 17,077 prompt tokens, 9,219 completion tokens.
- Completion reasoning tokens: 6,914.
- Prompt cache tokens reported by OpenRouter: 16,768.
- Planned tasks: 1 per unit.
- Mathlib requests: 7.
- Hydration exact identifiers: 6.
- Exact Lean-checked requests: 4 obvious requests checked directly:
  `Matrix.det_of_upperTriangular`, `Matrix.det_of_lowerTriangular`,
  `Nat.add_choose_eq`, and `Nat.Partition`.
- Failed direct requests: guessed FPS coefficient lemmas and
  `mul_left_cancel0`; fallback hydration produced 24 checked candidates.

### No-Reasoning Selector

Artifact:
`docs/latex-statement-context-runs/2026-05-06-dev-panel5-v1-paid-reasoning-none/`

- Model: `deepseek/deepseek-v4-flash`.
- `reasoning_effort`: `none`.
- Valid JSON: yes.
- Elapsed: 33.785 seconds.
- Cost: `$0.00300286`.
- Usage: 17,077 prompt tokens, 2,186 completion tokens.
- Completion reasoning tokens: 0.
- Planned tasks: 1 per unit.
- Mathlib requests: 7.
- Exact Lean-checked requests: only
  `Matrix.det_of_upperTriangular` and `Matrix.det_of_lowerTriangular`.
- Bad guesses included `Nat.vandermonde`, `IsInverse.unique`, and
  `NPartition.bijection`.
- Fallback hydration recovered the Vandermonde bridge facts:
  `Nat.add_choose_eq`,
  `Finset.Nat.sum_antidiagonal_eq_sum_range_succ`, and
  `Finset.Nat.sum_antidiagonal_eq_sum_range_succ_mk`.

## What This Shows

The five-unit panel gives richer data immediately. The single NPartition loop
was useful for debugging, but by itself it could not show whether a change was
generic or NPartition-shaped. The panel shows:

- The selectors understand the source mathematics at a coarse level on all five
  units.
- They still often invent API names; Lean hydration is required.
- Default reasoning had better Mathlib recall for Vandermonde and
  `Nat.Partition`, but was about 3.4x slower than no-reasoning selection in
  this run.
- No-reasoning selection is probably good enough for cheap triage and payload
  shape checks, but not enough to trust exact Mathlib/API names.
- Neither selector decomposed the NPartition unit into helper tasks in this
  batched prompt, even though prior single-unit helper-contract prompts could
  do so. That means the batched selector prompt still needs stronger generic
  helper-planning pressure.

## Recommendations

Use this panel before another one-theorem prompt retry:

1. Run budget payload generation first and inspect prompt size plus target-name
   leakage checks.
2. Run no-reasoning selection for cheap triage.
3. Hydrate all selected Mathlib requests with Lean tooling.
4. Escalate only failed or high-risk units to reasoning/stronger model
   selection.
5. Treat repeated `cannot_prove_from_visible_context` with checked context as a
   proof-synthesis routing signal, not another context-selector prompt target.
6. Keep a separate fresh held-out sample for actual benchmark claims. This panel
   is development data.

