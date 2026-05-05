# Source-Statement Local API Retrieval Preflight

Date: 2026-05-05

## Change

`scripts/run_source_statement_live_eval.py` now retrieves source-keyed local
API declarations from the target Lean file before the withheld target. Retrieved
blocks are materialized into the Lean prefix context, so a generated theorem can
refer to the displayed local APIs during verification.

The retrieval still withholds the target Lean statement and declaration name. It
only considers prior same-file `theorem`, `lemma`, `def`, and `abbrev`
declarations, ranks them by source labels/text keywords, and includes direct
prior same-file dependencies referenced by selected blocks.

Block extraction now stops at declaration/example/notation boundaries and trims
trailing doc-comment or attribute blocks, avoiding prompt noise from the next
declaration.

## API-Free Budget Check

Command:

```bash
UV_CACHE_DIR=/tmp/uv-cache-repoprover uv run python scripts/run_source_statement_live_eval.py \
  --records /tmp/repoprover-source-statement-preflight-passing-6.jsonl \
  --output /tmp/repoprover-source-statement-local-api-retrieval-budget-6d \
  --limit 6 \
  --sample-mode corpus-spread \
  --include-record-imports \
  --lake-cache-from algebraic-combinatorics \
  --budget-only
```

Result:

- Records selected: 6
- Paid calls: 0
- Estimated max OpenRouter cost for the six-record generation batch:
  `$0.180751635`
- Per-record estimated max range: `$0.029508660` to `$0.032476665`

Manual prompt inspection confirmed `Local API retrieval` blocks appear for the
determinant, FPS, binomial, and limits records, while
`theorem target` and `__repoprover_source_statement_check` do not appear in the
payloads.

## Shared-Project Preflight

Command:

```bash
UV_CACHE_DIR=/tmp/uv-cache-repoprover uv run python scripts/run_source_statement_live_eval.py \
  --records /tmp/repoprover-source-statement-preflight-passing-6.jsonl \
  --output /tmp/repoprover-source-statement-local-api-retrieval-preflight-6b \
  --limit 6 \
  --sample-mode corpus-spread \
  --include-record-imports \
  --lake-cache-from algebraic-combinatorics \
  --reuse-project \
  --preflight-only \
  --lean-timeout 90 \
  --concurrency 1
```

Result:

- Records selected: 6
- Preflight successes: 6/6
- Paid calls: 0
- Output tree size: about `21M`
- Wall time: about `160s`

An intermediate run passed only 5/6 because retrieval selected
`coeff_zero_mul_fps` and `coeff_mul_fps'` without their prior dependency
`coeff_mul_fps`. The final implementation includes direct same-file dependencies
of selected blocks, restoring the preflight to 6/6.

## Decision

Serial Lean verification with one reusable project is simple and not the
current bottleneck for this six-record slice. It attempts every row and writes
individual success/failure artifacts. The next paid step should remain
generation-only over this same small preflight-passing slice, then feed archived
paid results through the verifier consumer.
