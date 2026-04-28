# Minimal-Context Gold Standard and Budget Plan

This report turns the April 28 whiteboard request into an executable plan for
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

Live OpenRouter metadata on April 28, 2026 gave these catalog prices:

| Model | Context | Input/output per M tokens |
|---|---:|---:|
| `qwen/qwen3-coder` | 262k | $0.22 / $1.80 |
| `deepseek/deepseek-v4-pro` | 1,048k | $0.435 / $0.87 |
| `google/gemini-2.5-flash` | 1,048k | $0.30 / $2.50 |
| `z-ai/glm-5` | 202k | $0.60 / $2.08 |
| `z-ai/glm-5.1` | 202k | $1.05 / $3.50 |

The live key balance was `$7.42` when checked with
`GET https://openrouter.ai/api/v1/credits`. The earlier `$10` should be treated
as an intended budget, not the current balance.

The successful toy first-merge path used 181,115 input tokens and 3,585 output
tokens across sketch, math review, and engineering review. At current catalog
prices:

| Model | Toy first-merge cost | Runs with $7.42 | Runs with $10 | Runs with $50 |
|---|---:|---:|---:|---:|
| `qwen/qwen3-coder` | $0.0463 | 160 | 216 | 1,080 |
| `google/gemini-2.5-flash` | $0.0633 | 117 | 158 | 790 |
| `deepseek/deepseek-v4-pro` | $0.0819 | 91 | 122 | 611 |
| `z-ai/glm-5` | $0.1161 | 64 | 86 | 431 |
| `z-ai/glm-5.1` | $0.2027 | 37 | 49 | 247 |

Real chapter work will be much larger than the toy. A conservative planning
multiplier is 10x for a small early FPS chapter and 25x for a hard chapter with
multiple repair/review rounds. Under that range, `$7.42` is enough for roughly
6-16 bounded early-chapter attempts on `qwen/qwen3-coder`, or 3-9 attempts on
`deepseek/deepseek-v4-pro`. `$50` is enough for a real pilot over the first few
chapters plus several failure-driven review rounds.

## Immediate RepoProver Change

The new `--stop-after-first-merge` flag makes this budget plan practical. It
stops the coordinator as soon as the first approved PR lands, before maintainers
or follow-up proof agents start spending tokens. Use it with:

```bash
python -m repoprover run /tmp/repoprover-toy-gemini3-flash \
  --pool-size 1 \
  --provider openrouter \
  --model z-ai/glm-5.1 \
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
