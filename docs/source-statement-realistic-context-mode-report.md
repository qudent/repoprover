# Source-Statement Realistic Context Mode

Date: 2026-05-05

## Motivation

The 6/6 strict hard-slice result is useful, but it was not a fully realistic
book-autoformalization setting. Several prompt improvements used source-facing
Lean target doc comments, target-derived alignment labels, or hidden target
declaration names as internal guidance triggers. Those surfaces are good for
debugging, but they can overfit to the existing formalization.

This checkpoint adds an explicit prompt context mode:

- `target-comment`: the previous mode. It withholds the target Lean statement
  and name from the model, but still uses target Lean doc comments and
  target-derived alignment labels as source-facing focus metadata. It also keeps
  imported same-source-label API retrieval.
- `source-only`: the stricter mode. It removes target Lean doc comments,
  target-derived comment labels, hidden target-name guidance triggers, and
  imported source-label API retrieval. The prompt is driven by the TeX/source
  span, file/prefix context, prior same-file local APIs, local style examples,
  and generic domain guidance.

The new mode is selected with:

```bash
--context-mode source-only
```

## Zero-Cost Artifacts

Two source-only budget-only checkpoints were generated.

Strict six-row hard slice:

```bash
UV_CACHE_DIR=/tmp/uv-cache-repoprover uv run python scripts/run_source_statement_live_eval.py \
  --records docs/source-statement-runs/2026-05-05-strict-guidance-six-generation/eval/selected-records.jsonl \
  --output docs/source-statement-runs/2026-05-05-strict-guidance-six-source-only-budget \
  --limit 6 --sample-mode corpus-spread --include-record-imports \
  --lake-cache-from algebraic-combinatorics --budget-only \
  --context-mode source-only --max-tokens 32768 --reasoning-effort high
```

Result:

- paid calls: `0`
- actual cost: `$0.00`
- estimated max generation cost: `$0.18052935`

Broader 11-record preflight-passing slice:

```bash
UV_CACHE_DIR=/tmp/uv-cache-repoprover uv run python scripts/run_source_statement_live_eval.py \
  --records docs/source-statement-runs/2026-05-05-preflight-passing-11-generation/eval/selected-records.jsonl \
  --output docs/source-statement-runs/2026-05-05-preflight-passing-11-source-only-budget \
  --limit 11 --sample-mode corpus-spread --include-record-imports \
  --lake-cache-from algebraic-combinatorics --budget-only \
  --context-mode source-only --max-tokens 32768 --reasoning-effort high
```

Result:

- paid calls: `0`
- actual cost: `$0.00`
- estimated max generation cost: `$0.330879705`

Hidden-name check over the 11-record source-only prompt artifacts:

- absent `isSummable_of_coeffStabilizesTo_partial_sum`
- absent `fps_newtonBinomial_neg`
- absent `fps_comp_coeff_finite`
- absent `parts_eq_zero_of_partition_zero`
- absent `perm_pow_succ`
- absent `simpleTransposition_isSwap`
- absent `det_lowerTriangular`
- absent `coeffFinitelyDeterminedInProd_of_finite`
- absent `exists_xn_approximator`
- absent `binom_symm`
- absent `X_mul_eq_shift`

The row 1 source-only payload also has
`prefix_has_imported_label=false`, confirming that imported source-label API
retrieval is disabled in this mode.

## Context Gap Audit

The comparison tool:

```bash
UV_CACHE_DIR=/tmp/uv-cache-repoprover uv run python scripts/compare_source_statement_context_modes.py \
  --target-comment-run docs/source-statement-runs/2026-05-05-preflight-passing-11-generation \
  --source-only-run docs/source-statement-runs/2026-05-05-preflight-passing-11-source-only-budget \
  --output-json docs/source-statement-runs/2026-05-05-preflight-passing-11-source-only-budget/eval/context-mode-comparison.json \
  --output-md docs/source-statement-runs/2026-05-05-preflight-passing-11-source-only-budget/eval/context-mode-comparison.md
```

11-record result:

- rows with hidden target names in source-only payloads: `0`
- rows with target-comment terms absent from the source span: `7/11`
- source-only estimated max cost: `$0.330879705`

The same comparison over the strict six-row slice found `0` hidden target-name
hits and `5/6` rows where target-comment terms are absent from the source span.
That is the concrete context-selection gap: source-only prompts are cleaner, but
they often do not know which part of the TeX/source span the target formalizes.

## First Paid Source-Only Generation

The first paid realistic-context validation used the broader 11-record
preflight-passing slice:

```bash
UV_CACHE_DIR=/tmp/uv-cache-repoprover uv run python scripts/run_source_statement_live_eval.py \
  --records docs/source-statement-runs/2026-05-05-preflight-passing-11-generation/eval/selected-records.jsonl \
  --output docs/source-statement-runs/2026-05-05-preflight-passing-11-source-only-generation \
  --limit 11 --sample-mode corpus-spread --include-record-imports \
  --lake-cache-from algebraic-combinatorics --generation-only \
  --context-mode source-only \
  --max-actual-cost-usd 0.40 --concurrency 3 \
  --max-tokens 32768 --reasoning-effort high
```

Result:

- records generated: `11/11`
- paid calls: `11`
- actual cost: `$0.081084638`
- model: `deepseek/deepseek-v4-pro`
- Lean verification: not run in this generation checkpoint

Several generated declaration names already show statement-shape drift, for
example `det_triangular` for the lower-triangular determinant row and
`card_perm` for the permutation-power row. That is expected useful evidence:
source-only prompts are honest, but the current context selector still often
does not focus the exact intended theorem.

## What Changed In The Prompt

In `source-only` mode:

- `target_source_focus.target_declaration_source_comment` is `null`;
- `target_source_focus.record_comment_labels` is empty;
- `specific_source_labels` and `specific_labeled_parts` are not inferred from
  target-derived comments;
- hidden target declaration names are not used for domain-guidance triggers;
- imported declarations found only by matching source labels are not injected.
- `tex_source_focus` is added from the visible TeX/source span, including
  declared labels, referenced labels, theorem-like environments, source-keyword
  cues, part markers that are not merely inline `\ref{...} \textbf{(b)}`
  references, and broad-span risk flags.

This intentionally makes some prompts less helpful. For example, the
`fps_comp_coeff_finite` source-only prompt sees the source span label
`def.fps.subs`, but not the target doc-comment phrase “alternative coefficient
formula”. As a result, it does not receive the finite-coefficient
`finsum_eq_sum_of_support_subset` hint that the target-comment prompt received.
That is the point of this mode: it exposes where realistic context selection
needs to infer focus from TeX/source segmentation rather than from the target
Lean artifact.

## Tests

Focused tests passed:

```bash
UV_CACHE_DIR=/tmp/uv-cache-repoprover uv run pytest \
  tests/test_source_statement_live_eval.py \
  tests/test_source_statement_generation_artifacts.py
```

Result: `61 passed`.
After adding TeX-derived focus extraction, the same focused test set passes
with `63 passed`.

## Next Step

Use `source-only` as the default for realistic validation. The next work should
not be another hand-tuned six-row repair loop. It should verify the 11-record
source-only generation artifacts, classify the failures, and improve TeX/source
focus selection from those failures without reading target Lean comments or
names.
