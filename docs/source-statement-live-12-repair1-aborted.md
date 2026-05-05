# Source-Statement 12-Record Repair Probe, Aborted

Date: 2026-05-05

## Command

```bash
bash -ic 'UV_CACHE_DIR=/tmp/uv-cache-repoprover uv run python scripts/run_source_statement_live_eval.py \
  --output /tmp/repoprover-source-statement-live-12-repair1-20260505T004730Z \
  --limit 12 \
  --sample-mode stratified-easy \
  --include-record-imports \
  --repair-attempts 1 \
  --max-tokens 32768 \
  --max-actual-cost-usd 0.80 \
  --concurrency 3'
```

The run was manually stopped after verifier/materialization timeouts dominated
the first completed rows. Continuing would have spent provider budget without
measuring prompt quality.

Important follow-up: this command did not pass `--lake-cache-from
algebraic-combinatorics`, so each materialized `/tmp` project started setting up
its own Lake dependency tree. Future runs should first use `--preflight-only
--reuse-project --lake-cache-from algebraic-combinatorics --concurrency 1`, then
run paid calls only on records whose reusable project checks within timeout. A
one-record zero-cost smoke of that path succeeded at
`/tmp/repoprover-source-statement-preflight-reuse-1`; its output tree was about
`248K`.

## Result

- Paid OpenRouter responses received: 5
- Total reported OpenRouter cost from cost-summary artifacts: `$0.062798456`
- Partial result rows written before stop: 3
- Successes: 0
- Completed failure class: `materialization_or_lean_error`
- Repair attempts reached: 0
- Compact artifacts retained at:
  `/tmp/repoprover-source-statement-live-12-repair1-20260505T004730Z`
- Heavy generated Lean project directories were deleted after preserving JSON
  responses, cost summaries, prompts, and generated declarations. Tree size
  after cleanup: about `628K`.

## Completed Rows

| # | Record | Generated name | Cost | Verifier failure |
|---:|---|---|---:|---|
| 1 | `AlgebraicCombinatorics/Details/Limits.lean:PowerSeries.coeffStabilizesTo_partial_sum'` | `sum_lim` | `$0.0169679` | `lake build AlgebraicCombinatorics.FPS.Limits` timed out after 90s |
| 2 | `AlgebraicCombinatorics/DeterminantsBasic.lean:AlgebraicCombinatorics.Det.det_swap_cols` | `det_swap_cols` | `$0.02856384` | `lake env lean AlgebraicCombinatorics/DeterminantsBasic.lean` timed out after 90s |
| 3 | `AlgebraicCombinatorics/DeterminantsBasic.lean:AlgebraicCombinatorics.Det.det_add_smul_col` | `det_zero_col` | `$0.007527762` | `lake env lean AlgebraicCombinatorics/DeterminantsBasic.lean` timed out after 90s |

Two additional paid responses were received before the stop but did not reach a
partial result row:

- record 004, `coeff_derivative_eq`, generated `exists_derivative`, cost
  `$0.004417512`;
- record 006, `tsum'_eq_of_coeffStabilizesTo_partial_sum`, generated
  `isSummable_and_tsum_eq_coeffStabilizesTo_partial_sum`, cost `$0.005321442`.

## Interpretation

This probe did not validate or falsify the prompt/repair loop. The bottleneck
was the verifier path: materialized per-record projects were spending too much
time rebuilding or checking local imports, and the 90s Lean timeout was too low
for these records under fresh `/tmp` projects.

Before another paid source-statement batch:

1. Reuse a warmed Lake cache and the runner's `--reuse-project` mode so each
   record swaps only the generated target file inside one materialized project.
2. Add a `verifier_timeout`/`verifier_cache` preflight that runs without paid
   calls on the selected records and marks records whose local imports cannot be
   checked inside the configured timeout.
3. Prefer a smaller first live probe over records whose generated-only project
   can be checked cheaply, so OpenRouter spend measures prompt quality rather
   than build-system throughput.
