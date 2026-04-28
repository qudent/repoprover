# Minimal-Context Dataset Report

Run date: 2026-04-28.

## Artifacts

- Whole-corpus graph: `docs/minimal-context-graph.json`
- Whole-corpus records: `docs/minimal-context-full-records.jsonl`
- Whole-corpus format: `docs/minimal-context-format.md`
- Whole-corpus report: `docs/minimal-context-whole-corpus-report.md`
- Gold-candidate static review: `docs/minimal-context-gold-candidate-static-review.md`
- Canonical dataset: `docs/minimal-context-generated-records.jsonl`
- Batch 2 raw generation: `docs/minimal-context-generated-records-batch2.jsonl`
- Batch 2 Qwen3.6 regeneration: `docs/minimal-context-generated-records-batch2-qwen3.6-35b-a3b.jsonl`
- Batch 1 review: `docs/minimal-context-generated-review-qwen3-coder-report.md`
- Batch 2 review: `docs/minimal-context-generated-review-batch2-qwen3-coder-report.md`
- Batch 2 Qwen3.6 review: `docs/minimal-context-generated-review-batch2-qwen3.6-35b-a3b-report.md`
- Current model research: `docs/open-model-research-2026-04-28.md`
- Whole-corpus generator: `scripts/generate_context_graph.py`
- Generator: `scripts/generate_minimal_context_records.py`
- Reviewer: `scripts/review_minimal_context_records.py`

The whole-corpus artifacts contain 5,684 declaration-level records and a 6,573
node / 40,436 edge graph for the entire vendored book/formalization snapshot.
They are deterministic, local-only, and cost-free to regenerate. The canonical
reviewed JSONL currently contains 14 line-mapped records from
`AlgebraicCombinatorics/FPS/NotationsExamples.lean` lines 202-370. Each record
maps a Lean output region to TeX source spans, local predecessor declarations,
imports, Mathlib/API context, TeX-only inferability, trust scores, and reviewer
metadata.

The exact-label gold-candidate queue now contains 645 bounded records. The
deterministic static adversarial review accepts all 645 mechanically after
normalizing Lean subpart references to their parent TeX labels and stripping
Lean comments before scanning for `sorry`/`admit`. This pass is local and costs
`$0.00`; it is not a human semantic certification.

## Cost And Time

Estimated OpenRouter cost from recorded token usage:

| Phase | Records | Prompt tokens | Completion tokens | Estimated cost |
|---|---:|---:|---:|---:|
| Batch 1 generation | 4 | 11,790 | 2,201 | `$0.006556` |
| Batch 1 Qwen review | 4 | 10,681 | 1,505 | `$0.005059` |
| Batch 2 generation | 10 | 26,413 | 4,730 | `$0.014325` |
| Batch 2 Qwen review | 10 | 20,187 | 3,573 | `$0.010873` |
| Total recorded dataset work | 14 | 69,071 | 12,009 | `$0.036813` |
| Batch 2 Qwen3.6 regeneration | 10 | 27,304 | 7,115 | `$0.011269` |
| Batch 2 Qwen3.6 review | 10 | 22,709 | 7,729 | `$0.011121` |

Batch 2 generation ran in roughly 93 seconds wall time and recorded 72.5
seconds of model-call elapsed time across the 10 records. The batch 2 review
completed in about 37 seconds wall time. During the current continuation, the
OpenRouter credits endpoint moved from `$7.310344` remaining to `$7.287381`
remaining, a live debit of about `$0.022963`; token-estimated batch 2 spend was
`$0.025198`.

The Qwen3.6 rerun was done after checking the current OpenRouter catalog and
the official Qwen3.6 repository. `qwen/qwen3.6-35b-a3b` is now the default
open-weight Qwen model for these OpenRouter JSON generation/review scripts.
The run required `--reasoning-effort none`; without that parameter,
Qwen3.6-35B-A3B and Qwen3.6-27B both returned empty content on the first JSON
generation request.

## Review Outcomes

Current canonical dataset verdicts:

| Verdict | Count |
|---|---:|
| `provisionally_accept` | 1 |
| `revise` | 9 |
| `reject` | 4 |

The accepted seed is `binom_zero_of_lt`, a direct Mathlib wrapper where TeX,
Lean statement, and Mathlib lemma align closely. Rejected records are kept in
the dataset rather than dropped; they are useful hard negatives for context
selection because they expose TeX-to-Lean gaps.

## Difficulty Findings

The context-selection task is not just source-span retrieval. The hardest cases
require recognizing which Lean proof strategy replaces a short textbook
argument:

- TeX algebraic cancellation often becomes explicit natural-number division
  bookkeeping in Lean (`Dvd.intro`, `Nat.div_eq_iff_eq_mul_left`,
  `Nat.mul_div_cancel_left`).
- General textbook statements such as "any numbers" must be split into Lean
  domains and hypotheses, especially for `Nat` subtraction and positive-index
  Pascal identities.
- `Ring.choose` formalizations require typeclass context (`CommRing`,
  `BinomialRing`, `NatPowAssoc`) that the TeX notation does not state.
- Conceptually obvious theorem variants, such as additive binomial symmetry,
  are not directly present in the TeX and need explicit Mathlib API context.
- Double-factorial proofs are hard negatives: TeX motivates odd products, but
  Lean needs `Nat.doubleFactorial`, recurrence lemmas, local helper lemmas, and
  arithmetic tactics.

## Reproducibility Notes

Generate a new candidate batch with the current OpenRouter Qwen default:

```bash
uv run python scripts/generate_minimal_context_records.py \
  --chapter-id ac-notations-and-elementary-facts-examples \
  --lean-path AlgebraicCombinatorics/FPS/NotationsExamples.lean \
  --tex-path AlgebraicCombinatorics/tex/FPS/Notations.tex \
  --after-line 263 \
  --limit 10 \
  --tex-range 83:164 \
  --output docs/minimal-context-generated-records-batch2-qwen3.6-35b-a3b.jsonl \
  --model qwen/qwen3.6-35b-a3b \
  --reasoning-effort none
```

Review a candidate batch:

```bash
uv run python scripts/review_minimal_context_records.py \
  --records docs/minimal-context-generated-records-batch2-qwen3.6-35b-a3b.jsonl \
  --model qwen/qwen3.6-35b-a3b \
  --reasoning-effort none \
  --output docs/minimal-context-generated-review-batch2-qwen3.6-35b-a3b.jsonl \
  --summary docs/minimal-context-generated-review-batch2-qwen3.6-35b-a3b-report.md \
  --max-tokens 2048 \
  --source-context 3 \
  --lean-context 0
```
