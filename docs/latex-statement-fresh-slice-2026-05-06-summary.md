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

## Interpretation

This fresh slice is much harsher than the development panel. The current
pipeline can select and hydrate context cheaply, but generation with
`deepseek-v4-flash` at no reasoning often either declines after normalization or
produces shallow proof sketches with forbidden placeholders. The useful
engineering progress from the slice was in the verifier: support materialization
and semantic coverage now avoid two false rejects. The remaining failures need
repair/proof-synthesis lanes or stronger generation, not more theorem-specific
prompt hints.
