# Minimal Context DeepSeek Live Batch Plan

Generated API-free on 2026-05-02 from `docs/minimal-context-semantic-review-sample.jsonl` with:

```bash
UV_CACHE_DIR=/tmp/uv-cache-repoprover uv run python scripts/run_minimal_context_eval.py \
  --records docs/minimal-context-semantic-review-sample.jsonl \
  --project-root algebraic-combinatorics \
  --output /tmp/repoprover-oracle-context-deepseek-budget \
  --limit 5 \
  --max-tokens 8192 \
  --budget-only \
  --no-git
```

No paid OpenRouter calls were made. `OPENROUTER_API_KEY` was missing in the execution environment.

Price snapshot used by the script for `deepseek/deepseek-v4-pro`: OpenRouter public catalog, prompt `$0.435/M`, completion `$0.87/M`, context length `1,048,576`. Token counts are tokenizer-free estimates at 4 chars/token; actual OpenRouter usage/cost is captured after live calls in `eval/openrouter-response-cost-summary.json`.

## Budget summary: semantic-review smoke sample

- Model: `deepseek/deepseek-v4-pro`
- Records selected: 4 (the semantic-review sample currently yields 4 theorem/lemma records under the selector despite `--limit 5`)
- Estimated prompt tokens: 18,904
- Max completion tokens: 32,768
- Estimated max cost: $0.0367
- Paid calls made: `False`

## Budget summary: current oracle proof-fill dataset

API-free command run on the generated split:

```bash
UV_CACHE_DIR=/tmp/uv-cache-repoprover uv run python scripts/run_minimal_context_eval.py \
  --records docs/minimal-context-splits/oracle_proof_fill.jsonl \
  --project-root algebraic-combinatorics \
  --output /tmp/repoprover-oracle-proof-fill-budget \
  --force \
  --no-git \
  --budget-only \
  --limit 645 \
  --max-tokens 8192 \
  --reasoning-effort high
```

Result: the current selector picked 473 theorem/lemma records from the 645 split records; definitions/other chunks are not proof-fill targets under this runner.

- Records selected: 473
- Estimated prompt tokens: 2,030,412
- Max completion tokens: 3,874,816
- Estimated prompt cost: $0.8832
- Estimated max completion cost: $3.3711
- Estimated max total cost: $4.2543
- Per-record estimated max cost: min $0.0081, median $0.0088, P90 $0.0097, max $0.0133
- Prompt size: median 3,947 tokens, P90 6,028 tokens, max 14,193 tokens
- `OPENROUTER_API_KEY` present during this run: `False`
- Paid calls made: `False`

| # | Record | Prompt chars | Est. prompt tokens | Max completion | Est. max cost |
|---:|---|---:|---:|---:|---:|
| 1 | `AlgebraicCombinatorics/FPS/InfiniteProducts.lean:PowerSeries.coeffFinitelyDeterminedInProd_of_finite` | 12,593 | 3,149 | 8,192 | $0.0085 |
| 2 | `AlgebraicCombinatorics/FPS/InfiniteProducts.lean:PowerSeries.multipliable_coeff_eq_of_determines` | 16,800 | 4,200 | 8,192 | $0.0090 |
| 3 | `AlgebraicCombinatorics/FPS/InfiniteProducts.lean:PowerSeries.fubini_prod_invertible` | 33,440 | 8,360 | 8,192 | $0.0108 |
| 4 | `AlgebraicCombinatorics/FPS/InfiniteProducts.lean:PowerSeries.coeff_mul_one_add_eq_of_coeff_zero` | 12,777 | 3,195 | 8,192 | $0.0085 |

## Exact live commands

Run only after confirming `OPENROUTER_API_KEY` and budget. Each command still requires explicit `--call-openrouter`.

```bash
OPENROUTER_API_KEY=$OPENROUTER_API_KEY uv run python scripts/run_minimal_context_eval.py --records docs/minimal-context-semantic-review-sample.jsonl --project-root algebraic-combinatorics --output /tmp/repoprover-oracle-context-deepseek-budget/live-01 --record-id AlgebraicCombinatorics/FPS/InfiniteProducts.lean:PowerSeries.coeffFinitelyDeterminedInProd_of_finite --force --call-openrouter --model deepseek/deepseek-v4-pro --max-tokens 8192 --reasoning-effort high --no-git
```

```bash
OPENROUTER_API_KEY=$OPENROUTER_API_KEY uv run python scripts/run_minimal_context_eval.py --records docs/minimal-context-semantic-review-sample.jsonl --project-root algebraic-combinatorics --output /tmp/repoprover-oracle-context-deepseek-budget/live-02 --record-id AlgebraicCombinatorics/FPS/InfiniteProducts.lean:PowerSeries.multipliable_coeff_eq_of_determines --force --call-openrouter --model deepseek/deepseek-v4-pro --max-tokens 8192 --reasoning-effort high --no-git
```

```bash
OPENROUTER_API_KEY=$OPENROUTER_API_KEY uv run python scripts/run_minimal_context_eval.py --records docs/minimal-context-semantic-review-sample.jsonl --project-root algebraic-combinatorics --output /tmp/repoprover-oracle-context-deepseek-budget/live-03 --record-id AlgebraicCombinatorics/FPS/InfiniteProducts.lean:PowerSeries.fubini_prod_invertible --force --call-openrouter --model deepseek/deepseek-v4-pro --max-tokens 8192 --reasoning-effort high --no-git
```

```bash
OPENROUTER_API_KEY=$OPENROUTER_API_KEY uv run python scripts/run_minimal_context_eval.py --records docs/minimal-context-semantic-review-sample.jsonl --project-root algebraic-combinatorics --output /tmp/repoprover-oracle-context-deepseek-budget/live-04 --record-id AlgebraicCombinatorics/FPS/InfiniteProducts.lean:PowerSeries.coeff_mul_one_add_eq_of_coeff_zero --force --call-openrouter --model deepseek/deepseek-v4-pro --max-tokens 8192 --reasoning-effort high --no-git
```
