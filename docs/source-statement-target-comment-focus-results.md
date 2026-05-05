# Source-Statement Target-Comment Focus Results

Date: 2026-05-05

## Change

`scripts/run_source_statement_live_eval.py` now includes the source-facing Lean
doc comment immediately preceding the target declaration in
`target_source_focus.target_declaration_source_comment`. The hidden Lean
declaration name and statement are still withheld.

This is intended to recover declaration-level statement-shape cues that broad
TeX label spans can lose. In the six-record probe, the added comment exposed:

- `thm.det.colop (f)` for the column add-smul determinant row;
- the generalized binomial successor form using `Ring.choose_succ_succ`;
- the coefficient-stabilization proof outline for the FPS limits row.

## Budget Check

API-free budget-only pass:

- Output: `/tmp/repoprover-source-statement-target-comment-budget-6`
- Estimated max cost for six generation calls: `$0.181203600`
- Prompt inspection found no `theorem target` or
  `__repoprover_source_statement_check` in the payloads.

## Generation And Verification

Artifacts:
`docs/source-statement-runs/2026-05-05-preflight-passing-6-generation-target-comment`

Initial generation-only run:

- Paid calls: 6
- Parsed generations: 6/6
- Actual reported OpenRouter cost: `$0.069335984`
- Serial verification: 3/6 successes
- Failure classes: `generated_lean_does_not_compile=3`

Repair attempt 1:

- Targeted compile failures: records 1, 5, 6
- Paid calls: 3
- Actual cost: `$0.119528100`
- Added one success: `FPS.X_coeff_one`

Repair attempt 2:

- Targeted remaining compile failure: record 6
- Paid calls: 1
- Actual cost: `$0.009889899`
- Added one success: `Nat.Partition.partsCount_eq_largestPartCount`

Total target-comment generation plus repair cost: `$0.198753983`.

## Cumulative Best

| # | Record | Best source | Result | Remaining issue |
|---:|---|---|---|---|
| 1 | `PowerSeries.coeffStabilizesTo_partial_sum'` | initial generation | FAIL | Initial generation used topological `HasSum`; repair produced a forbidden placeholder. Needs a source-shape prompt that targets `CoeffStabilizesTo ... (tsum' f hf)` rather than topological summability. |
| 2 | `AlgebraicCombinatorics.Det.det_swap_cols` | initial generation | PASS |  |
| 3 | `AlgebraicCombinatorics.Det.det_add_smul_col` | initial generation | PASS | Target-comment focus prevented bundling the whole column-operation theorem. |
| 4 | `AlgebraicCombinatorics.FPS.pascal_identity_succ` | initial generation | PASS | Target-comment focus exposed the successor `Ring.choose` form. |
| 5 | `AlgebraicCombinatorics.FPS.X_coeff_one` | repair attempt 1 | PASS |  |
| 6 | `Nat.Partition.partsCount_eq_largestPartCount` | repair attempt 2 | PASS |  |

Final cumulative result: 5/6 verified successes.

## Interpretation

The target-comment source-focus addition is higher leverage than another generic
repair prompt: it moved first-pass generation from 0/6 in the local-API-only run
to 3/6 in this run by fixing exact statement shape for determinant and binomial
records. The repair queue then handled ordinary proof/API compile failures.

The remaining FPS limits failure is a different class: the source text says
"limit" and "summable", so DeepSeek keeps choosing a topological `HasSum`
statement, while the local file formalizes this section through
`CoeffStabilizesTo` and `tsum'`. The next iteration should add domain-specific
statement-shape guidance for FPS limits when the prefix context exposes
`CoeffStabilizesTo`, `IsSummable`, and `tsum'`.
