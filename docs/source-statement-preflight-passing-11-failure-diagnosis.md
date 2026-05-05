# Source-Statement 11-Record Failure Diagnosis

Date: 2026-05-05

Input run:
`docs/source-statement-runs/2026-05-05-preflight-passing-11-generation`

Best cumulative result from the run is 5/11 verified successes:

- first-pass successes: rows 2, 4, 8;
- repair-attempt-1 successes: rows 5, 6;
- repair-attempt-2 successes: none.

## Remaining Failure Buckets

| # | Record | Best failure | Diagnosis |
|---:|---|---|---|
| 1 | `PowerSeries.isSummable_of_coeffStabilizesTo_partial_sum'` | hidden grader mismatch | Generated a bundled theorem proving `IsSummable f ∧ tsum' ... = L`; local target likely expects a narrower theorem. This is a statement-shape issue, not a compile issue after using a 180s verifier timeout. |
| 3 | `AlgebraicCombinatorics.fps_newtonBinomial_neg` | hidden grader mismatch after repair | Repair compiles but leaves typeclass metavariables around `BinomialRing`; exact target shape or explicit type arguments are still wrong. |
| 7 | `AlgebraicCombinatorics.fps_comp_coeff_finite` | generated Lean compile failure after two repairs | The model repeatedly uses nonmatching `finsum` helper APIs. Latest error applies `finsum_eq_sum` with arguments shaped for a finite set rather than the finite-support proof expected by Lean. |
| 9 | `Nat.Partition.parts_eq_zero_of_partition_zero` | generated Lean compile failure after two repairs | Generated proof invents nonexistent `Nat.Partition.entries` and `Nat.Partition.sum_eq` fields. Needs local partition representation/API retrieval before another repair. |
| 10 | `AlgebraicCombinatorics.perm_pow_succ` | generated Lean compile failure after two repairs | Generated proof uses nonexistent `Equiv.mul_apply`. Needs current permutation/function-coercion API guidance. |
| 11 | `AlgebraicCombinatorics.simpleTransposition_isSwap` | hidden grader mismatch | Generated the equality theorem `simpleTransposition_eq_transposition`, which compiles, but the hidden target expects `Perm.IsSwap s[i]`. Needs statement-shape guidance for `IsSwap`, not another compiler repair. |

## Retry Guidance

- Do not spend more on generic compiler-feedback retries for rows 7, 9, or 10;
  they already failed a second repair pass.
- Rows 1, 3, and 11 need visible-context statement-shape diagnostics or
  targeted local API retrieval before another paid attempt.
- Row 9 specifically needs local partition constructor/projection context;
  field-style guesses are the wrong repair path.
- Row 10 needs a small local permutation-power example showing how functions
  coerce and compose in the current Lean/mathlib environment.

This diagnosis preserves the target-statement-withheld benchmark boundary: it
uses generated declarations and verifier/grader errors, not hidden gold text, to
classify the remaining failures.
