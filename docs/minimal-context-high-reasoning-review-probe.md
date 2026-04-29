# Minimal-Context High-Reasoning Review Probe

## Model Choice

The current best OpenRouter-available open-weight/FOSS reasoning model for this
review task appears to be `deepseek/deepseek-v3.2-speciale`.

Evidence checked on April 29, 2026:

- OpenRouter lists `deepseek/deepseek-v3.2-speciale` with 163,840 context,
  reasoning support, structured outputs, and model-weight link.
- The Hugging Face model card lists the license as MIT and says the repository
  and model weights are MIT licensed.
- OpenRouter describes Speciale as the high-compute V3.2 variant optimized for
  maximum reasoning and agentic performance.

`qwen/qwen3.6-35b-a3b` remains the best cheap open-weight Qwen option for this
harness: Apache 2.0, 262,144 context, structured outputs, and much faster JSON
behavior. It is not the strongest open-weight reasoning model available on
OpenRouter.

## Probe Setup

Input:

- `docs/minimal-context-semantic-review-sample.jsonl`

Command shape:

```bash
uv run python scripts/review_minimal_context_records.py \
  --records docs/minimal-context-semantic-review-sample.jsonl \
  --source-root algebraic-combinatorics \
  --model deepseek/deepseek-v3.2-speciale \
  --reasoning-effort high \
  --max-tokens 8192 \
  --output docs/minimal-context-semantic-review-deepseek-v3.2-speciale-high.jsonl \
  --summary docs/minimal-context-semantic-review-deepseek-v3.2-speciale-high.md
```

The first single-record smoke with `--max-tokens 3072` failed: the model spent
the entire cap on hidden reasoning and returned empty content. The same record
with `--max-tokens 8192` produced parseable JSON.

## Result

The full run was intentionally stopped after 3 records because it was too slow
and token-heavy for an uninspected 24-row pass.

Partial artifact:

- `docs/minimal-context-semantic-review-deepseek-v3.2-speciale-high.jsonl`
- `docs/minimal-context-semantic-review-deepseek-v3.2-speciale-high.md`

Observed rows:

| Record | Verdict | Prompt | Completion | Estimated cost |
|---|---:|---:|---:|---:|
| `SymmetricPolynomials.P` | `revise` | 4,063 | 7,720 | `$0.010889` |
| `IversonBracket.iverson` | `parse_error` | 2,816 | 8,192 | `$0.010957` |
| `CauchyBinet.submatrixOfFinset` | `revise` | 4,485 | 4,967 | `$0.007754` |

Total partial cost: `$0.029600`.

## Readout

Speciale-high gives sharper import-minimality criticism than Qwen. It called out
specific replacement imports and aggressively flagged unnecessary `open`,
`variable`, and broad `Mathlib` context.

It is not yet a good bulk reviewer:

- high reasoning is slow, taking minutes per row;
- one of three rows hit the 8,192 completion cap and produced malformed JSON;
- it overfocuses on strict import minimization, sometimes treating convenient
  umbrella imports as invalid or unacceptable rather than merely non-minimal.

Use Speciale-high as a small adjudicator or hard-case critic, not as the default
24-row or 645-row reviewer.

## Segmentation Problems

The current problems are mostly semantic segmentation problems, not mechanical
line validity problems:

- TeX labels often cover a whole multi-part definition, but a Lean target is one
  subpart or one helper declaration.
- Lean declaration ranges can include neighboring doc blocks or notation
  declarations because the parser segments from declaration start to the next
  declaration start.
- Source spans are label-bounded, so they can include examples or following
  prose that are useful for reading but not minimal.
- Lean context can include file-scope namespace, open, variable, and typeclass
  assumptions that are sufficient for compilation but not minimal for one
  declaration.
- Broad imports like `Mathlib` make context sufficient while hiding the smaller
  import set a strict minimal-context benchmark might want.

The earlier segmentation/problem report is:

- `docs/minimal-context-semantic-review-analysis.md`

The older generation overview is:

- `docs/minimal-context-generation-report.md`
