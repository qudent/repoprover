# Minimal-Context Gold Standard and Budget Plan

This report turns the April 28 planning request into an executable plan for
using the existing Algebraic Combinatorics formalization as supervision for
future RepoProver runs.

## Goal

Build a gold standard of "minimal context" examples:

- output chunk: one Lean declaration, a small declaration cluster, or a proof
  block from the completed formalization;
- source context: the smallest LaTeX spans needed to justify that chunk;
- Lean context: the exact predecessor definitions, notation, imports, and
  lemmas whose syntax the new formalization should reuse;
- dependency confidence: explicit trust scores for the source span, Lean
  dependency graph, model extraction, and human review state.

The point is not to regenerate the whole book immediately. The first useful
product is a small, reviewed benchmark that says what an agent should have read
before writing a known-good formalization chunk.

## External Baseline

The published formalization repository has enough structure for a first pass
without cloning the whole repo:

- `manifest.json` has 45 chapters and 344 target theorem labels.
- `CONTENTS.md` reports 340 proved targets and 4 exercise/cited-style leftovers.
- TeX and Lean paths line up well enough for chapter-level pairing. Examples:

| Chapter source | TeX size | Lean target | Lean size |
|---|---:|---|---:|
| `AlgebraicCombinatorics/tex/FPS/Notations.tex` | 1,028 lines | `AlgebraicCombinatorics/FPS/NotationsExamples.lean` | 931 lines |
| `AlgebraicCombinatorics/tex/FPS/CommutativeRings.tex` | 428 lines | `AlgebraicCombinatorics/FPS/CommutativeRings.lean` | 723 lines |
| `AlgebraicCombinatorics/tex/FPS/FPSDefinition.tex` | 974 lines | `AlgebraicCombinatorics/FPSDefinition.lean` | 831 lines |

These first chapters are a better pilot than the partition chapter: they are
early in the dependency order, not too large, and they establish syntax that
later chapters reuse.

## Gold-Standard Record

Use JSONL so examples can be reviewed incrementally and fed to prompt or
retrieval benchmarks without requiring a database:

```json
{
  "id": "ac-fps-notations:def.binom.binom",
  "chapter_id": "ac-notations-and-elementary-facts-examples",
  "output": {
    "lean_path": "AlgebraicCombinatorics/FPS/NotationsExamples.lean",
    "declaration_names": ["..."],
    "line_range": [120, 160],
    "chunk_kind": "definition_cluster"
  },
  "minimal_context": {
    "source_spans": [
      {
        "path": "AlgebraicCombinatorics/tex/FPS/Notations.tex",
        "line_range": [40, 90],
        "labels": ["def.binom.binom"]
      }
    ],
    "lean_predecessors": [
      {
        "path": "AlgebraicCombinatorics/FPS/NotationsExamples.lean",
        "declaration": "...",
        "reason": "exact notation reused"
      }
    ],
    "imports": ["Mathlib"]
  },
  "trust": {
    "source_span": 0.55,
    "lean_dependency_graph": 0.45,
    "model_extraction": 0.35,
    "human_review": 0.0
  },
  "review_notes": []
}
```

Trust starts low for agent-produced context. It rises only when a cheaper model
and a stronger reviewer agree, or when a human spot-checks the span. If a later
formalization attempt fails because a required ancestor was omitted, reduce
`lean_dependency_graph` for that example and add the missed dependency as a
negative example.

## Six-Hour Execution Plan

1. Create chapter pairs from the published `manifest.json`, `CONTENTS.md`, and
   GitHub tree metadata.
2. For the first one to three FPS chapters, split Lean files into declarations
   with local predecessor windows. Start with definitions and theorem statements;
   full proof chunks are second priority.
3. Use a cheap OpenRouter model to propose minimal source spans and predecessor
   declarations for 20-40 chunks.
4. Run a second cheap reviewer model on the same records with a strict task:
   find missing context, oversized context, and label mismatches.
5. Manually inspect the worst disagreements and keep the ugly examples. The
   benchmark is more valuable if it preserves failures.
6. Feed the reviewed records into RepoProver prompts as retrieval examples, then
   run bounded first-merge smokes with `--stop-after-first-merge`.

## Budget Estimate

Live OpenRouter metadata refreshed on April 28, 2026 gave these catalog prices:

| Model | Context | Input/output per M tokens |
|---|---:|---:|
| `qwen/qwen3.6-35b-a3b` | 262k | $0.1612 / $0.96525 |
| `qwen/qwen3.6-27b` | 256k | $0.325 / $3.25 |
| `qwen/qwen3.6-plus` | 1,000k | $0.325 / $1.95 |
| `deepseek/deepseek-v4-pro` | 1,048k | $0.435 / $0.87 |
| `qwen/qwen3-coder-next` | 262k | $0.14 / $0.80 |
| `moonshotai/kimi-k2.6` | 256k | $0.7448 / $4.655 |
| `google/gemini-2.5-flash` | 1,048k | $0.30 / $2.50 |
| `z-ai/glm-5.1` | 202k | $1.05 / $3.50 |

The live key balance was `$7.22` when checked with
`GET https://openrouter.ai/api/v1/credits`. The earlier `$10` should be treated
as an intended budget, not the current balance.

The successful toy first-merge path used 181,115 input tokens and 3,585 output
tokens across sketch, math review, and engineering review. At current catalog
prices:

| Model | Toy first-merge cost | Runs with $7.22 | Runs with $10 | Runs with $50 |
|---|---:|---:|---:|---:|
| `qwen/qwen3.6-35b-a3b` | $0.0415 | 174 | 241 | 1,206 |
| `qwen/qwen3.6-27b` | $0.0862 | 84 | 116 | 580 |
| `qwen/qwen3-coder` | $0.0575 | 126 | 174 | 869 |
| `google/gemini-2.5-flash` | $0.0633 | 117 | 158 | 790 |
| `deepseek/deepseek-v4-pro` | $0.1084 | 67 | 92 | 461 |
| `moonshotai/kimi-k2.6` | $0.1919 | 38 | 52 | 260 |
| `z-ai/glm-5.1` | $0.2644 | 27 | 38 | 189 |

Real chapter work will be much larger than the toy. A conservative planning
multiplier is 10x for a small early FPS chapter and 25x for a hard chapter with
multiple repair/review rounds. Under that range, `$7.22` is enough for roughly
7-17 bounded early-chapter attempts on `qwen/qwen3.6-35b-a3b`, or 2-6 attempts
on `z-ai/glm-5.1`. `$50` is enough for a real pilot over the first few
chapters plus several failure-driven review rounds.

`qwen/qwen3-coder` remains in this report only as historical evidence from
earlier runs. The current Qwen/OpenRouter default for minimal-context JSON
generation and review is `qwen/qwen3.6-35b-a3b` with
`--reasoning-effort none`.

## Immediate RepoProver Change

The new `--stop-after-first-merge` flag makes this budget plan practical. It
stops the coordinator as soon as the first approved PR lands, before maintainers
or follow-up proof agents start spending tokens. Use it with:

```bash
python -m repoprover run /tmp/repoprover-toy-gemini3-flash \
  --pool-size 1 \
  --provider openrouter \
  --model qwen/qwen3.6-35b-a3b \
  --no-background-agents \
  --stop-after-first-merge \
  --verbose
```

Use `scripts/estimate_openrouter_budget.py` after each run to recompute costs
from the actual JSONL token logs and current model prices.

## First Pilot Records

`docs/minimal-context-pilot-records.jsonl` contains three low-trust pilot
records for the first FPS chapter. They came from one `qwen/qwen3-coder`
OpenRouter extraction pass over raw GitHub excerpts, followed by a line-number
sanity check. The recorded API usage was 11,582 prompt tokens and 404 completion
tokens, costing `$0.0038658`.

Treat these records as a scaffold, not gold. The next useful step is a reviewer
pass that tries to break each record by finding missing source context, missing
Mathlib/Lean predecessor context, or overly broad clusters.

## First Reviewer Pass

`scripts/review_minimal_context_records.py` now runs an evidence-backed
OpenRouter audit over the JSONL records. It fetches the corresponding TeX and
Lean snippets from `facebookresearch/algebraic-combinatorics`, asks a reviewer
model for structured JSON, records token usage and estimated price, and writes a
Markdown report.

Two live reviewer attempts were run on April 28, 2026:

| Model | Result | Prompt/completion tokens | Estimated cost |
|---|---|---:|---:|
| `deepseek/deepseek-v4-pro` | Transport and billing worked, but the model returned empty message content after spending the 4,096 completion-token cap on hidden reasoning. Kept as a provider failure record. | 13,819 / 12,288 | `$0.016702` |
| `qwen/qwen3-coder` | Produced parseable JSON reviews for all three updated records; final verdicts were revise / provisionally_accept / revise. | 11,793 / 1,350 | `$0.005024` |

The Qwen review marked all three records as still needing revision. Durable
fixes already applied to `docs/minimal-context-pilot-records.jsonl`:

- clipped reviewer evidence to the declared Lean output range, after a first
  audit pass leaked neighbor declarations and produced a false `binom_neg_one`
  finding;
- added missing binomial proof dependencies such as `Nat.cast_ne_zero`,
  `Nat.factorial_ne_zero`, `nsmul_eq_mul`, and `npow_one`;
- expanded the Pascal identity source span to include the sentence introducing
  the cited basic facts;
- added explicit Pascal identity proof/typeclass context including
  `BinomialRing`, `NatPowAssoc`, `Nat.succ_pred_eq_of_pos`,
  `Nat.pred_eq_sub_one`, and `Nat.sub_add_cancel`.
- replaced broad `Mathlib` imports in the three pilot records with imports that
  were checked by `lake env lean` against the extracted output ranges:
  `Mathlib.Data.Finset.Powerset` plus `Mathlib.Data.Finset.Prod` for the
  cardinality principles, and `Mathlib.RingTheory.Binomial` for both binomial
  clusters.

The current records remain low-trust because no human has reviewed them and
because the exact imported modules have only been checked for these isolated
output ranges, not for full chapter integration.

## Generated Candidate Batch

`scripts/generate_minimal_context_records.py` now generates candidate records
directly from real upstream TeX/Lean chunks. It splits a Lean file into
declaration chunks, gives a bounded TeX excerpt to an OpenRouter model, and
writes JSONL records with:

- `generation`: timestamp, model, source base URL, elapsed seconds, token usage,
  and estimated OpenRouter cost;
- `trust`: capped unreviewed trust scores so model output cannot certify itself;
- `tex_only_inferability`: an explicit assessment of how much the Lean chunk
  can be inferred from textbook LaTeX without prior formalization/API context.

The first generated batch is
`docs/minimal-context-generated-records.jsonl`. It covers four next-binomial
chunks from `NotationsExamples.lean` lines 202-261:

- `binom_neg_one`
- `binom_factorial_formula`
- `prod_odd_eq_doubleFactorial`
- `factorial_dvd_prod_odd_mul_pow`

The committed generation pass used `qwen/qwen3-coder` and cost `$0.006556`
for 11,790 prompt tokens and 2,201 completion tokens. The follow-up adversarial
review in `docs/minimal-context-generated-review-qwen3-coder-report.md` cost
`$0.005059` for 10,681 prompt tokens and 1,505 completion tokens. Its verdicts
were revise, revise, reject, revise, which is useful: the double-factorial
support record is a concrete hard negative showing that the textbook span alone
does not explain enough Lean/API context.

After refreshing model availability, the batch-2 generation/review workflow was
rerun with `qwen/qwen3.6-35b-a3b` and `--reasoning-effort none`. The new
generation artifact cost `$0.011269` for 27,304 prompt and 7,115 completion
tokens; the new adversarial review cost `$0.011121` for 22,709 prompt and 7,729
completion tokens. The Qwen3.6 review verdicts were 1 provisionally accepted,
6 revise, and 3 reject.
