# Source-Statement Larger-Slice Results

Date: 2026-05-05

## Zero-Cost Preflight

Command shape:

```bash
UV_CACHE_DIR=/tmp/uv-cache-repoprover uv run python scripts/run_source_statement_live_eval.py \
  --records docs/minimal-context-splits/oracle_source_statement.jsonl \
  --output /tmp/repoprover-source-statement-preflight-domain-guidance-24 \
  --limit 24 --sample-mode corpus-spread --include-record-imports \
  --lake-cache-from algebraic-combinatorics --preflight-only \
  --reuse-project --concurrency 1 --lean-timeout 90
```

Result:

- Selected records: 24
- Preflight successes: 8/24
- Failure classes: `verifier_preflight_failed=15`,
  `verifier_preflight_error=1`
- Provider spend: `$0.00`
- Output tree: `/tmp/repoprover-source-statement-preflight-domain-guidance-24`
  (`89M`)

The 8 preflight-passing records were extracted to:
`/tmp/repoprover-source-statement-domain-guidance-preflight-passing-8.jsonl`.

## Paid Eight-Record Run

Artifacts:
`docs/source-statement-runs/2026-05-05-preflight-passing-8-generation-domain-guidance`

API-free budget estimate for the 8 passing records:

- Estimated max generation cost: `$0.239763300`

Generation-only run:

- Paid calls: 8
- Parsed generations: 8/8
- Actual reported OpenRouter cost: `$0.051891150`
- Serial verification: 2/8 successes
- Failure classes:
  `generated_lean_does_not_compile=5`,
  `grader_gold_statement_not_proved=1`

Repair attempt 1:

- Targeted generated-only compile failures: records 1, 3, 4, 6, and 7
- Paid calls: 5
- Actual reported OpenRouter cost: `$0.050338200`
- Verified repair successes: 1/5 (`Nat.Partition.size_eq`)

Total eight-record generation plus repair cost: `$0.102229350`.

## Cumulative Result

| # | Record | First pass | Repair | Best result | Remaining issue |
|---:|---|---|---|---|---|
| 1 | `PowerSeries.comp_prod_infinite` | FAIL | FAIL | FAIL | Still uses topology-oriented `Multipliable`/`tprod` APIs that do not fit the local non-topological context. |
| 2 | `AlgebraicCombinatorics.Det.det_swap_cols` | PASS | n/a | PASS |  |
| 3 | `AlgebraicCombinatorics.eq_of_embedUnivInBiv_eq` | FAIL | FAIL | FAIL | Needs exact coefficient projection context for `embedUnivInBiv`; generated theorem shape is close but proof cannot simplify the bivariate coefficient. |
| 4 | `AlgebraicCombinatorics.fps_subs_X_right` | FAIL | FAIL | FAIL | Needs better local substitution API guidance; generated proof almost reduces to a single coefficient case but gets the `coeff_X_pow` side condition wrong. |
| 5 | `AlgebraicCombinatorics.FPS.coeff_mul_X_pow` | FAIL | n/a | FAIL | Generated theorem compiled but did not imply the withheld target statement; this was not repaired because repair prompts intentionally use only generated-only compiler feedback. |
| 6 | `Nat.Partition.size_eq` | FAIL | PASS | PASS | Repair used the existing partition field proof. |
| 7 | `AlgebraicCombinatorics.simpleTransposition_apply_of_ne` | FAIL | FAIL | FAIL | Repair compiled but still did not imply the withheld target; theorem shape was too strong/different. |
| 8 | `AlgebraicCombinatorics.lexLt_irrefl` | PASS | n/a | PASS |  |

Final cumulative result for this larger paid slice: 3/8 verified successes.

## Interpretation

The six-record slice is solved by the current prompt plus one repair pass, but
the larger slice shows the next bottleneck: context selection and domain API
guidance do not yet generalize enough across FPS substitution/infinite-products,
multivariate FPS coefficient extraction, and exact statement-shape matching.

The pipeline behavior is still good operationally:

- provider generation is decoupled from Lean checking;
- all paid responses are logged in per-record artifacts before verification;
- serial Lean verification attempts every saved row and records individual
  success/failure signals;
- repair prompts use generated-only compiler output and do not expose hidden
  grader statements.

The next iteration should use the failed rows from this 8-record run as hard
examples before spending on a broader paid slice.
