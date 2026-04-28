# Minimal-Context Semantic Review Analysis

## Hypothesis

A small stratified model review of the 645 mechanically accepted records should
find whether the remaining task is mostly semantic minimality, line-boundary
cleanup, or basic record validity.

## Run

- Sample input: `docs/minimal-context-semantic-review-sample.jsonl`
- Final review JSONL: `docs/minimal-context-semantic-review-qwen3.6-35b-a3b.jsonl`
- Final review Markdown: `docs/minimal-context-semantic-review-qwen3.6-35b-a3b.md`
- Reviewer: `qwen/qwen3.6-35b-a3b`
- OpenRouter settings: `--reasoning-effort none`, `response_format={"type":"json_object"}`
- Evidence source: local `algebraic-combinatorics/` snapshot
- Final artifact usage: 99,565 prompt tokens, 27,994 completion tokens,
  estimated `$0.043071`
- Actual exploratory spend: about `$0.115251` by credit-balance delta, because
  the first full pass was discarded after the evidence bundle was found to omit
  predecessor snippets, then one malformed `SSYT` response was retried.

## Results

| Verdict | Count |
|---|---:|
| `provisionally_accept` | 4 |
| `revise` | 14 |
| `reject` | 6 |
| `parse_error` | 0 |

Provisionally accepted records:

- `AlgebraicCombinatorics/Partitions/Basics.lean:IversonBracket.iverson`
- `AlgebraicCombinatorics/FPS/InfiniteProducts.lean:PowerSeries.coeff_mul_one_add_eq_of_coeff_zero`
- `AlgebraicCombinatorics/SymmetricFunctions/MonomialSymmetric.lean:AlgebraicCombinatorics.SymmetricFunctions.fintype_of_size`
- `AlgebraicCombinatorics/SymmetricFunctions/SchurBasics.lean:SkewSSYT`

Rejected records:

- `AlgebraicCombinatorics/SymmetricFunctions/Definitions.lean:AlgebraicCombinatorics.SymmetricPolynomials.P_isAlgebra'`
- `AlgebraicCombinatorics/SymmetricFunctions/Definitions.lean:AlgebraicCombinatorics.SymmetricPolynomials.P_isCommRing'`
- `AlgebraicCombinatorics/SymmetricFunctions/NPartition.lean:NPartition`
- `AlgebraicCombinatorics/SymmetricFunctions/Definitions.lean:AlgebraicCombinatorics.SymmetricPolynomials.S`
- `AlgebraicCombinatorics/Permutations/Basics.lean:AlgebraicCombinatorics.Permutation`
- `AlgebraicCombinatorics/LaurentSeries.lean:AlgebraicCombinatorics.laurentPolynomial_algebra`

## What Was Hard

The main failure mode is not label alignment. The static pass already removed
obvious label and line-range errors. The semantic difficulty is deciding which
Lean context is truly minimal when declarations depend on file-scope variables,
namespaces, typeclass assumptions, inherited structures, and broad imports.

Recurring issues in the 24-row sample:

- broad `Mathlib` imports make records sufficient but not minimal;
- file-scope variables, namespace openings, and section assumptions are not
  always represented as predecessor context;
- some source labels describe a multi-part mathematical definition while the
  Lean target is one small declaration;
- output line ranges sometimes include neighboring comments or notation;
- local predecessor mappings are necessary, but the review harness must
  materialize their snippets to judge sufficiency.

## Harness Fixes

During review, the first full pass exposed a bug in the semantic-review harness:
it showed the reviewer predecessor metadata but not the actual mapped predecessor
snippets. `scripts/review_minimal_context_records.py` now supports
`--source-root`, includes predecessor snippets in the evidence bundle, and asks
OpenRouter for JSON-object responses to avoid malformed-review artifacts.

Focused validation:

```bash
uv run pytest tests/test_minimal_context_review.py
```

## Next Step

Before spending on a larger review, improve the deterministic generator in two
places:

1. Add file-scope context nodes for namespaces, section variables, and typeclass
   assumptions.
2. Add an import-minimization or import-attribution pass so records can separate
   "sufficient via `Mathlib`" from "minimal Lean context".

After that, rerun the 24-record semantic review and compare verdict movement
against this baseline.
