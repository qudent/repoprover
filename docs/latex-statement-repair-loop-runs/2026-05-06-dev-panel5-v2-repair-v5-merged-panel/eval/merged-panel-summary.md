# Merged Panel Summary

Artifact: `docs/latex-statement-repair-loop-runs/2026-05-06-dev-panel5-v2-repair-v5-merged-panel/`

This is a development-panel merged artifact, not a held-out benchmark. It combines the five-unit v2 panel generation, the split repair-loop output, and the focused unit-004 bridge-rewrite repair. Gold declarations remain hidden from selector/generator/repair prompts and are used only by post-hoc semantic graders.

## Headline

- Generated-only verification: `3/5` compiled, with `2` clean cannot-prove declines and no compile failures.
- Post-hoc semantic coverage: `3/5` source units prove all aligned gold declarations, covering `4/6` aligned gold declarations.
- Effective provider cost for this artifact path: `$0.0244708072`.

## Unit Outcomes

| Unit | Source | Outcome |
|---|---|---|
| `unit-001` | `lem.fps.prod.irlv.cong-div` | clean `cannot_prove_from_visible_context` |
| `unit-002` | `thm.det.triang` | compiles and semantic coverage passes for both aligned upper/lower triangular gold theorems |
| `unit-003` | `thm.commring.inverse-uni` | compiles and semantic coverage passes |
| `unit-004` | `prop.binom.vandermonde.NN` | compiles and semantic coverage passes after focused bridge-rewrite repair |
| `unit-005` | `prop.sf.Npar-as-par` | clean `cannot_prove_from_visible_context` |

## Pipeline Lessons

- Repair loops must preserve panel structure: multi-unit repair outputs need per-unit batches and per-unit generation payloads, otherwise verifier import/context inference can false-reject preserved units.
- The Vandermonde failure was not missing context; the model knew the right checked theorem names but needed compiler feedback and a generic rewrite-order rule for bridge lemmas.
- Triangular determinant was a semantic-grader bridge failure: the generated theorem has a bundled `BlockTriangular` disjunction, while the source/gold surface has separate upper/lower entrywise-zero hypotheses. A generic pointwise-hypothesis/`Or.inl`/`Or.inr` grader bridge proves the aligned gold statements from the generated theorem.
- FPS division and NPartition are proof-synthesis/context-depth blockers, not JSON/schema/transport failures.
