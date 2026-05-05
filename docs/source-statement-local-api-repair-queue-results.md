# Source-Statement Local API Repair Queue Results

Date: 2026-05-05

## What Changed

Added `scripts/repair_source_statement_generation.py`, an artifact-consumer
repair generator for archived source-statement runs. It reads
`verification-results.json`, targets generated-only compile failures by default,
builds repair prompts from:

- the original source-statement prompt payload;
- the failed generated declaration;
- generated-only Lean compiler output;
- the same retrieved local API context.

It writes `repair-attempt-NNN-*` artifacts into each record directory and does
not run Lean. Verification stays in
`scripts/verify_source_statement_generation.py`, which now accepts
`--model-output-name` and `--output-prefix` so repaired outputs can be checked in
a separate serial Lean queue.

The grader was also fixed to try the generated theorem's own binder order before
the gold theorem's binder order. This matters when a model proves the same
statement with reordered explicit binders, for example generated `(k n)` versus
gold `(n k)`.

## Run

Base generation run:
`docs/source-statement-runs/2026-05-05-preflight-passing-6-generation-local-api`

Costs:

- Initial generation: `$0.041165848`
- Repair attempt 1: `$0.050071313`
- Repair attempt 2: `$0.019003323`
- Repair attempt 3: `$0.002774459`
- Total local-API generation plus repair cost: `$0.113014943`

All repair generation calls were provider-only. Lean checks were run afterward
with the reusable-project verifier.

## Verification Progress

| Stage | Paid calls | Verified successes | Generated-only compile failures | Grader mismatches | Notes |
|---|---:|---:|---:|---:|---|
| Initial local-API generation | 6 | 0/6 | 5 | 1 | Local retrieval changed behavior but did not pass rows. |
| Repair attempt 1 | 5 | 2/6 | 2 | 1 plus original Nat binomial mismatch | Fixed `det_swap_cols` and `X_coeff_one`. |
| Repair attempt 2 | 2 | 2/6 cumulative | 1 | 3 | `sum_lim` and partition records compiled or narrowed, but still needed more work. |
| Repair attempt 3 | 1 | 3/6 cumulative | 0 | 3 | Fixed the partition proof; grader-order fix was required to recognize it. |

Final cumulative best rows:

| # | Record | Best source | Result | Remaining issue |
|---:|---|---|---|---|
| 1 | `PowerSeries.coeffStabilizesTo_partial_sum'` | repair attempt 2 | FAIL | Generated theorem compiles, but hidden grader statement has a different exact shape/typeclass expectation. |
| 2 | `AlgebraicCombinatorics.Det.det_swap_cols` | repair attempt 1 | PASS |  |
| 3 | `AlgebraicCombinatorics.Det.det_add_smul_col` | repair attempt 1 | FAIL | Generated theorem compiles, but bundles column-swap plus add-smul instead of the exact target. |
| 4 | `AlgebraicCombinatorics.FPS.pascal_identity_succ` | initial generation | FAIL | Generated Nat `choose` theorem compiles but misses generalized `Ring.choose` target. |
| 5 | `AlgebraicCombinatorics.FPS.X_coeff_one` | repair attempt 1 | PASS |  |
| 6 | `Nat.Partition.partsCount_eq_largestPartCount` | repair attempt 3 | PASS |  |

## Interpretation

The repair queue is useful: after local API retrieval, generated-only compiler
feedback repaired all compile failures in this six-record slice, moving the
cumulative result from 0/6 to 3/6 verified successes. The remaining failures are
not Lean syntax/API problems; they are exact target-shape failures.

The next iteration should spend less on generic compile repair and more on
source-focus/statement-shape control:

- prevent bundled multi-part theorem statements when the record focus identifies
  one part;
- bias generalized binomial records toward `Ring.choose` when that API appears
  in retrieved local context;
- handle limits records without introducing topological theorem shapes that are
  broader than the source/gold target.
