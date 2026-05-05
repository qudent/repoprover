# Source-Statement Strict Guidance Generation Result

Date: 2026-05-05

This records the paid retry after tightening prompt constraints from the 0/6
targeted-guidance run.

## Generation

Command:

```bash
bash -ic 'UV_CACHE_DIR=/tmp/uv-cache-repoprover uv run python scripts/run_source_statement_live_eval.py \
  --records /tmp/repoprover-targeted-guidance-six-failures.jsonl \
  --output docs/source-statement-runs/2026-05-05-strict-guidance-six-generation \
  --limit 6 --sample-mode corpus-spread --include-record-imports \
  --lake-cache-from algebraic-combinatorics --generation-only \
  --max-actual-cost-usd 0.25 --concurrency 3 \
  --max-tokens 32768 --reasoning-effort high'
```

Result:

- provider responses: `6/6`
- parsed generations: `6/6`
- paid calls: `6`
- actual reported cost: `$0.0308386`
- provider artifacts committed before verification in commit `e123672`

## Serial Verification

Command:

```bash
UV_CACHE_DIR=/tmp/uv-cache-repoprover uv run python scripts/verify_source_statement_generation.py \
  --run-output docs/source-statement-runs/2026-05-05-strict-guidance-six-generation \
  --work-root /tmp/repoprover-strict-guidance-six-verify \
  --lake-cache-from algebraic-combinatorics --include-record-imports \
  --workers 1 --lean-timeout 180 --output-prefix verification-180
```

Result:

- verified successes: `2/6`
- failure classes: `generated_lean_does_not_compile=3`,
  `grader_gold_statement_not_proved=1`

| # | Record | Generated name | Result |
|---:|---|---|---|
| 1 | `PowerSeries.isSummable_of_coeffStabilizesTo_partial_sum'` | `isSummable_of_partial_sum_coeffStabilizesTo` | PASS |
| 2 | `AlgebraicCombinatorics.fps_newtonBinomial_neg` | `fps_newton_binom` | compile failure: integer power/coercion misuse and failed `lift` tactic |
| 3 | `AlgebraicCombinatorics.fps_comp_coeff_finite` | `fps_comp_coeff_finite` | compile failure: support-subset proof leaves `d ≤ n` unsolved |
| 4 | `Nat.Partition.parts_eq_zero_of_partition_zero` | `partition_of_zero_parts_empty` | PASS |
| 5 | `AlgebraicCombinatorics.perm_pow_succ` | `perm_pow_apply_eq_iterate` | generated-only compiles, but hidden grader fails because the model still chose pointwise iteration instead of the group-power statement |
| 6 | `AlgebraicCombinatorics.simpleTransposition_isSwap` | `simpleTransposition_isSwap` | compile failure: close to the right `IsSwap` shape, but `omega` cannot prove one `Fin` bound |

## Interpretation

The stricter source-comment-derived constraints recovered two of the six hard
rows and confirmed that prompt shape matters. The remaining failures no longer
justify another fresh broad-generation pass:

- rows 2, 3, and 6 are generated-only compile failures and are candidates for a
  single compiler-feedback repair pass;
- row 5 is a statement-shape mismatch and needs a statement-shape-first stage or
  stronger direct source-comment contract, not compiler repair.

This also continues to support the queue design: provider generation, artifact
logging, and serial Lean verification are operationally decoupled.

## Repair Attempt 1

Targeted rows: `2`, `3`, and `6`, the generated-only compile failures from the
strict-guidance verification.

Command:

```bash
bash -ic 'UV_CACHE_DIR=/tmp/uv-cache-repoprover uv run python scripts/repair_source_statement_generation.py \
  --run-output docs/source-statement-runs/2026-05-05-strict-guidance-six-generation \
  --verification-results verification-180-results.json \
  --generated-only-lean-name verification-180-generated-only-lean.json \
  --attempt 1 --indices 2 3 6 \
  --max-tokens 32768 --reasoning-effort high \
  --max-actual-cost-usd 0.12 --concurrency 3'
```

Result:

- paid calls: `3`
- parsed repair generations: `2/3`
- actual reported cost: `$0.166295128`
- caveat: this exceeded the requested cap because the old repair queue launched
  all three concurrent calls before accounting for reserved estimated cost;
  `scripts/repair_source_statement_generation.py` has since been patched to
  reserve estimated cost before launch.

Verification command:

```bash
UV_CACHE_DIR=/tmp/uv-cache-repoprover uv run python scripts/verify_source_statement_generation.py \
  --run-output docs/source-statement-runs/2026-05-05-strict-guidance-six-generation \
  --work-root /tmp/repoprover-strict-guidance-six-repair-verify \
  --lake-cache-from algebraic-combinatorics --include-record-imports \
  --workers 1 --lean-timeout 180 \
  --model-output-name repair-attempt-001-model-output.json \
  --output-prefix repair-attempt-001-verification
```

Repair verification:

- row 2 repair still fails generated-only; it misapplies
  `fps_onePlusX_pow_neg'` with an explicit type argument where Lean expects the
  natural exponent.
- row 3 repair returned invalid model JSON, so there is no repair declaration to
  verify.
- row 6 repair passes generated-only and hidden-grader verification.

Cumulative strict-guidance hard-slice result after repair: `3/6` verified
successes for `$0.197133728` across strict generation plus repair. The successes
are rows `1`, `4`, and `6`.

## Shape-Warning Repair

After adding the no-gold diagnostic
`pointwise_iteration_instead_of_group_power_statement`, a shape-warning-only
repair targeted row `5`.

Command:

```bash
bash -ic 'UV_CACHE_DIR=/tmp/uv-cache-repoprover uv run python scripts/repair_source_statement_generation.py \
  --run-output docs/source-statement-runs/2026-05-05-strict-guidance-six-generation \
  --verification-results verification-180-results.json \
  --generated-only-lean-name verification-180-generated-only-lean.json \
  --attempt 2 --include-shape-warnings --shape-warnings-only \
  --shape-diagnostic-results shape-diagnostic-results.json \
  --indices 5 --max-tokens 32768 --reasoning-effort high \
  --max-actual-cost-usd 0.04 --concurrency 1'
```

Result:

- paid calls: `1`
- parsed repair generations: `1/1`
- actual reported cost: `$0.006123669`
- generated statement: `α ^ (n + 1) = α ^ n * α`

The first verifier attempt exposed a checker-side binder parser issue: the
generated theorem had a binder `(α : Equiv.Perm X)`, but the application
candidate parser missed the Unicode binder name and tried bad applications. The
parser now handles nested type binders and Unicode Lean identifiers.

Reverification with the fixed checker:

```bash
UV_CACHE_DIR=/tmp/uv-cache-repoprover uv run python scripts/verify_source_statement_generation.py \
  --run-output docs/source-statement-runs/2026-05-05-strict-guidance-six-generation \
  --work-root /tmp/repoprover-strict-guidance-six-shape-repair-verify-fixed \
  --lake-cache-from algebraic-combinatorics --include-record-imports \
  --workers 1 --lean-timeout 180 \
  --model-output-name repair-attempt-002-model-output.json \
  --output-prefix repair-attempt-002-verification-fixed
```

Row `5` passes generated-only and hidden-grader verification.

Cumulative strict-guidance hard-slice result after repair and shape-warning
repair: `4/6` verified successes for `$0.203257397` across strict generation
plus repairs. The successes are rows `1`, `4`, `5`, and `6`.
