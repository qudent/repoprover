# Source-Statement Preflight-Passing Six Diagnosis

Date: 2026-05-05

## Run

Generation artifacts:
`docs/source-statement-runs/2026-05-05-preflight-passing-6-generation`

Generation command used `--generation-only --concurrency 3`, so OpenRouter
calls were decoupled from Lean checks and all paid artifacts were written to the
repo before verification.

Verification command used one reusable Lean project:

```bash
UV_CACHE_DIR=/tmp/uv-cache-repoprover uv run python scripts/verify_source_statement_generation.py \
  --run-output docs/source-statement-runs/2026-05-05-preflight-passing-6-generation \
  --work-root /tmp/repoprover-source-statement-verify-preflight-passing-6-serial \
  --include-record-imports \
  --lake-cache-from algebraic-combinatorics \
  --workers 1 \
  --lean-timeout 90
```

## Result

- OpenRouter cost: `$0.079889403`
- Generation success: 6/6 parsed DeepSeek outputs
- Verification success: 0/6
- Serial verification time: `167.93s`
- Verifier disk use: about `20M`
- Failure classes:
  - `generated_lean_does_not_compile`: 5
  - `grader_gold_statement_not_proved`: 1

## Failure Themes

| # | Record | Generated name | Failure | Diagnosis |
|---:|---|---|---|---|
| 1 | `PowerSeries.coeffStabilizesTo_partial_sum'` | `sum_lim` | generated does not compile | Invented local `where Summable ...` and `tsum ...`; syntax invalid for theorem-local definitions and mismatches existing local API. |
| 2 | `Det.det_swap_cols` | `det_colop` | generated does not compile | Uses stale or unavailable helper names: `det_swap_rows`, `Matrix.submatrix_transpose`. |
| 3 | `Det.det_add_smul_col` | `det_colop` | generated does not compile | Formalized a bundled multi-part theorem and invented APIs such as `Matrix.updateColumn`, `det_zero_row`, `det_add_mul_row`. |
| 4 | `FPS.pascal_identity_succ` | `binom_rec` | grader not proved | Generated a valid Nat `choose` theorem, but the hidden target is about local `Ring.choose`; this is a semantic/context-selection mismatch. |
| 5 | `FPS.X_coeff_one` | `x_coeff_spec` | generated does not compile | Statement bundles both coefficient facts; proof uses `simp` where it makes no progress. This resembles the earlier case fixed by generated-only repair. |
| 6 | `Nat.Partition.partsCount_eq_largestPartCount` | `partsCount_eq_card_filter_largestPart` | generated does not compile | Uses plausible local names but unfolds `numParts`, which is not in the displayed target expression; likely needs exact local theorem/API snippets around partition transpose. |

## Next Prompt/Context Changes

Implemented after this diagnosis:

- Forbid theorem-local `where` definitions and local redefinitions of concepts
  already likely present in context.
- Add a stronger rule that every helper theorem/API used in the proof must
  appear in prefix/local examples or retrieved API snippets, unless it is a
  very standard Mathlib theorem.
- Make multi-part source focus stricter: if the selected record is one theorem,
  do not bundle sibling determinant operation facts.
- For local notation and local domain APIs, include examples that show the exact
  namespace/type family, for example `Ring.choose` vs `Nat.choose`.

Still missing:

- Add local API retrieval for nearby declarations whose names overlap generated
  unknown identifiers or source labels without leaking the withheld target
  declaration name.
- Rerun a small generation-only probe after the prompt/context update and
  compare against this 0/6 baseline.

Trust scoring should still wait. This run did not mostly succeed at independent
source-statement generation, so generated statements are not yet reliable enough
to become a feed-forward dependency graph.
