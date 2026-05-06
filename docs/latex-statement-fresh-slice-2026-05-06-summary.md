# Fresh Five-Unit LaTeX Statement Slice

Generated: `2026-05-06T09:25Z`

This slice is recorded in
`docs/latex-statement-fresh-slice-2026-05-06.json`. It was chosen from
gold-candidate LaTeX statement units that were not mentioned in prior run
artifacts outside the base datasets. It is fresh evidence for this first run;
after this point it is development evidence, not held out.

## Artifacts

- Budget payload:
  `docs/latex-statement-panel-runs/2026-05-06-fresh-slice5-budget/`
- Paid selector/generation:
  `docs/latex-statement-panel-runs/2026-05-06-fresh-slice5-paid-v1/`
- No-cost rerun after support/semantic verifier fixes:
  `docs/latex-statement-panel-runs/2026-05-06-fresh-slice5-paid-v1-support-scoped-rerun/`
- Failed 4k repair-context attempt:
  `docs/latex-statement-repair-loop-runs/2026-05-06-fresh-slice5-repair-v1-paid/`
- Compact 8k one-round repair loop:
  `docs/latex-statement-repair-loop-runs/2026-05-06-fresh-slice5-repair-v1-paid-v2-compact/`

## Cost And Scale

- Selector model: `deepseek/deepseek-v4-flash`, `reasoning_effort=none`.
- Generation model: `deepseek/deepseek-v4-flash`, `reasoning_effort=none`.
- Selector prompt: 28,677 tokens; completion: 2,431 tokens; cost:
  `$0.0064647`.
- Generation prompts: 43,029 tokens total; completions: 2,447 tokens total;
  cost: `$0.0062877416`.
- Total paid provider cost for this fresh-slice run: `$0.0127524416`.
- Hydration: 10 requested Mathlib/project names, 9 exact checked identifiers,
  and 8 checked fallback identifiers.
- First paid repair-context call cost `$0.00738948` but hit the 4,096-token
  output cap and produced invalid JSON. The prompt now asks for compact bounded
  JSON and the repair-loop default cap is 8,192 tokens.
- Compact repair-loop v2 cost `$0.01428308` total:
  `$0.00679938` repair-context selection plus `$0.0074837` repair generation.
  It hydrated 8 checked signatures and 2 fallback-resolved context requests.
- Targeted signed-sum repair cost `$0.00240898`. It used the same checked
  context but a generic finiteness/representation prompt rule, converting the
  bad Lean compile failure into a clean `cannot_prove_from_visible_context`
  decision. The merged artifact is
  `docs/latex-statement-repair-loop-runs/2026-05-06-fresh-slice5-unit004-finiteness-merged/`.

## Results

Initial verification of the paid outputs compiled `0/5`. That exposed a
verifier/materialization bug: visible support variables from unrelated prior
contexts could leak globally, making a valid FPS field corollary appear to
require `[Algebra ℚ K]`. The verifier now scopes visible variables around the
snippet they belong to.

After rerunning verification with scoped support, generated-only compile is
`1/5`: `cor.fps.invertible.field` compiles. Semantic coverage initially still
false-rejected it because semantic coverage did not reuse the verified open
context. The semantic grader now reuses the verified opens from the generation
verification batch, and semantic coverage proves `1/5`.

Per-unit outcome after the no-cost rerun:

| Unit | Source | Outcome |
|---|---|---|
| `unit-001` | `cor.lgv.catalan-hankel-det-0` | normalized to clean cannot-prove; raw output contained `sorry` scratch |
| `unit-002` | `cor.fps.invertible.field` | compiles and semantic coverage proves the aligned gold theorem |
| `unit-003` | `prop.binom.nCk-2i-qedmo.CN` | normalized to clean cannot-prove; raw output contained `sorry` scratch |
| `unit-004` | `lem.cancel.all-even.l1` | compile failure; model used `Fin d → ℤ` where project context uses `Fin d → ZMod 2`, and guessed unavailable `Finset.piFinset` |
| `unit-005` | `thm.sf.jt-e` | normalized to clean cannot-prove; raw output contained `sorry` scratch |

One compact repair round preserved the successful FPS unit but did not improve
the fresh-slice compile count: verification stayed `1/5`, with three clean
declines and one signed-sum compile failure. The selector did produce valid,
hydrated context, but the remaining blockers are not JSON transport problems.
For `lem.cancel.all-even.l1`, the model still used the impossible finite carrier
`Fin d → ℤ` and claimed a `Fintype` route that Lean rejects. For the Catalan
Hankel and Jacobi-Trudi-e units, the model concluded that visible source and
local predecessor context lack the needed project definitions/proof
infrastructure. For the binomial identity, checked `PowerSeries.coeff_mul`
context was not enough for the generator to construct the proof.

A targeted proof-lane retry on `unit-004` fixed the failure classification. The
prompt now includes a generic warning that a finite source choice space must not
be enlarged to all functions into an infinite codomain, because there is no
generic `Fintype (α → ℤ)`. The model then correctly identified the needed
finite sign-vector carrier as `Fin d → ZMod 2` and declined because the visible
context lacked a working `signProduct` bridge proof. After overlaying that
one-unit result back onto the five-unit run, generated-only verification is
`1/5` with failure classes `{compiled: 1, declined_cannot_prove: 4}` and
semantic coverage remains `1/5`, proving the FPS aligned gold theorem.

The current proof-lane handoff for this merged run is
`docs/latex-statement-proof-lane-tasks/2026-05-06-fresh-slice5-finiteness-merged/`.
It contains target-hidden tasks for the four remaining clean declines:
`unit-001`, `unit-003`, `unit-004`, and `unit-005`. The task builder keeps only
visible source/prompt/verifier context plus compact semantic coverage status,
and strips aligned Lean targets and post-hoc semantic check/count metadata. A
leakage scan found no hidden target names or gold metadata patterns in the
generated JSON/Markdown tasks.

## Interpretation

This fresh slice is much harsher than the development panel. The current
pipeline can select and hydrate context cheaply, but generation with
`deepseek-v4-flash` at no reasoning often either declines after normalization or
produces shallow proof sketches with forbidden placeholders. The useful
engineering progress from the slice was in the verifier and loop robustness:
support materialization and semantic coverage now avoid two false rejects, and
repair-context JSON failures are recoverable. The remaining failures need
repair/proof-synthesis lanes, better local/project context acquisition, or
stronger generation, not theorem-specific prompt hints.
