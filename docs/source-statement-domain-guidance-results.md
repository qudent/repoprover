# Source-Statement Domain-Guidance Results

Date: 2026-05-05

## Change

The source-statement prompt now has three additional context mechanisms:

- source-label retrieval from already imported local Lean modules, prompt-only;
- FPS statement-shape guidance for coefficientwise limits, the indeterminate
  `X`, and coefficient APIs;
- partition-transpose guidance that warns against stale/guessed APIs such as
  `Finset.card_congr` and field notation for `numParts`/`largestPart`.

Imported source-label snippets are no longer copied into the generated Lean file
because those declarations are already available through imports. This avoids
duplicate declaration failures while still showing the API to the model.

## API-Free Budget Check

Output: `/tmp/repoprover-source-statement-domain-guidance-budget-6`

- Selected records: 6
- Estimated max generation cost: `$0.182075775`
- Paid calls: 0
- Prompt inspection found no `theorem target`,
  `__repoprover_source_statement_check`, API key, bearer token, or OpenRouter
  secret marker.

## Paid Run

Artifacts:
`docs/source-statement-runs/2026-05-05-preflight-passing-6-generation-domain-guidance`

Generation-only run:

- Paid calls: 6
- Parsed generations: 6/6
- Actual reported OpenRouter cost: `$0.031387338`
- Serial verification: 4/6 successes
- Failure classes: `generated_lean_does_not_compile=2`

Repair attempt 1:

- Targeted compile failures: records 3 and 6
- Paid calls: 2
- Actual reported OpenRouter cost: `$0.031858820`
- Verified repair successes: records 3 and 6

Total domain-guidance generation plus repair cost: `$0.063246158`.

## Cumulative Result

| # | Record | First pass | Repair | Best result |
|---:|---|---|---|---|
| 1 | `PowerSeries.coeffStabilizesTo_partial_sum'` | PASS | n/a | PASS |
| 2 | `AlgebraicCombinatorics.Det.det_swap_cols` | PASS | n/a | PASS |
| 3 | `AlgebraicCombinatorics.Det.det_add_smul_col` | FAIL | PASS | PASS |
| 4 | `AlgebraicCombinatorics.FPS.pascal_identity_succ` | PASS | n/a | PASS |
| 5 | `AlgebraicCombinatorics.FPS.X_coeff_one` | PASS | n/a | PASS |
| 6 | `Nat.Partition.partsCount_eq_largestPartCount` | FAIL | PASS | PASS |

Final cumulative result for this six-record slice: 6/6 verified successes.

## Interpretation

This is the first run where one prompt family plus one generated-only compiler
feedback repair pass verifies every row in the preflight-passing six-record
slice. The important improvement over the prior target-comment run is that the
FPS limits row now succeeds on first generation by using the imported
`coeffStabilizesTo_partial_sum` API, while the `X` coefficient row also succeeds
on first generation after adding explicit coefficient-API guidance.

The remaining open scaling question is whether this survives a larger slice.
The next cheap validation should use the same generation-only plus separate
Lean-verifier queue on a larger preflight-passing set, with provider calls still
fully logged before verification.
