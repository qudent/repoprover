# Source-Statement Shared-Project Preflight Report

Date: 2026-05-05

## Command

```bash
UV_CACHE_DIR=/tmp/uv-cache-repoprover uv run python scripts/run_source_statement_live_eval.py \
  --output /tmp/repoprover-source-statement-preflight-reuse-12 \
  --limit 12 \
  --sample-mode stratified-easy \
  --include-record-imports \
  --lake-cache-from algebraic-combinatorics \
  --reuse-project \
  --preflight-only \
  --lean-timeout 90 \
  --concurrency 1
```

## Result

- Paid calls: 0
- Records selected: 12
- Preflight successes: 6/12
- Output tree size: about `73M`
- Failure classes:
  - `verifier_preflight_failed`: 4
  - `verifier_preflight_error`: 2

This confirms the shared-project verifier path avoids the earlier per-record
hundreds-of-MB project trees. The remaining failures are now real verifier input
quality or timeout issues rather than dependency cloning.

## Passing Records

- `PowerSeries.coeffStabilizesTo_partial_sum'`
- `AlgebraicCombinatorics.Det.det_swap_cols`
- `AlgebraicCombinatorics.Det.det_add_smul_col`
- `AlgebraicCombinatorics.FPS.pascal_identity_succ`
- `AlgebraicCombinatorics.FPS.X_coeff_one`
- `Nat.Partition.partsCount_eq_largestPartCount`

These are the best candidates for the next small paid probe.

## Failing Records

| # | Record | Failure |
|---:|---|---|
| 4 | `AlgebraicCombinatorics.FPS.coeff_derivative_eq` | bad generated-file scope close: missing `end Definition` before `end AlgebraicCombinatorics.FPS` |
| 5 | `AlgebraicCombinatorics.FPS.Laurent.T_isUnit` | bad generated-file scope close: missing `end LaurentPolynomialBasics` |
| 6 | `PowerSeries.tsum'_eq_of_coeffStabilizesTo_partial_sum` | copied/imported local context still contains unresolved `Seq.StabilizesTo` facts and sorry/unreachable-tactic noise |
| 9 | `AlgebraicCombinatorics.laurentPolynomial_T_isUnit'` | bad generated-file scope close: missing `end LaurentPolynomials` |
| 11 | `Equiv.Perm.sign_coe_eq_neg_one_pow_invCount` | building `AlgebraicCombinatorics.Permutations.Inversions1` timed out after 90s |
| 12 | `skewSchurPoly_isSymmetric` | building imported symmetric-function modules timed out after 90s |

## Next Gate

The next paid source-statement probe should select only preflight-passing
records, use `--reuse-project --lake-cache-from algebraic-combinatorics
--concurrency 1`, and stay under a small cap such as `$0.30`.

Before spending more on the failed half, fix generated context closing for
nested namespaces/sections and decide whether records requiring heavy local
imports should be a separate benchmark bucket.
