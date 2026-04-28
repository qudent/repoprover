# RepoProver Toy Model Experiments

This guide records the bounded toy validation runs from April 27, 2026. The goal was not to run a full book proof, but to validate the local RepoProver loop against the toy Lean project.

## Commit Map

- `57421d3` in this repo: baseline local setup, provider/model CLI support, OpenRouter support, and toy Lean build validation.
- `956b452` in this repo: Gemini 3 Flash provider result recorded in the coordination notes that are now consolidated into `STATUS.md`.
- `97c3bd9` in `/tmp/repoprover-toy-gemini3-flash`: GLM 5.1 sketch commit, `Sketch basics chapter: define double and prove three theorems`.
- `ed17e510` in `/tmp/repoprover-toy-gemini3-flash`: merge commit for the accepted GLM 5.1 sketch PR.
- `eef1daf` in `/tmp/repoprover-toy-gemini3-flash`: coordinator-generated follow-up target theorem issues after the sketch merge.

Use `git show <hash>` in the relevant repository to inspect each commit.

## Model Selection

Gemini 3 Flash was tested through Google’s OpenAI-compatible endpoint. The working model string was:

```bash
gemini-3-flash-preview
```

The plain `gemini-3-flash` string returned 404. Google’s model docs list Gemini 3 Flash as a preview model and link tool/thinking behavior, including thought signatures.

On April 27, 2026, the shared tool loop was updated to preserve provider-specific fields on assistant tool calls instead of rebuilding only `id`, `type`, and `function`. This keeps Google's OpenAI-compatible `extra_content.google.thought_signature` metadata in the replayed assistant message. A live `gemini-3-flash-preview` smoke with one function call and one continuation passed after the change:

```text
stop_reason=stop, iterations=2, tool_calls=["echo_marker"], final_text="FINAL: gemini3-smoke"
```

For the April 27 OpenRouter open-weight attempt, `z-ai/glm-5.1` was selected first. Live OpenRouter model metadata described it as a coding model with long-horizon-task gains; it also passed a direct OpenRouter chat smoke. Other reasonable candidates visible at that time were `deepseek/deepseek-v4-pro`, `qwen/qwen3-coder`, and `qwen/qwen3-coder-plus`.

On April 28, 2026, model availability was refreshed against the live
OpenRouter catalog and the official Qwen3.6 repository. Qwen3.6 is now the
current Qwen family, and OpenRouter lists `qwen/qwen3.6-35b-a3b`,
`qwen/qwen3.6-27b`, `qwen/qwen3.6-plus`, `qwen/qwen3.6-flash`, and
`qwen/qwen3.6-max-preview`. The current open-weight Qwen default for
minimal-context JSON generation/review is therefore `qwen/qwen3.6-35b-a3b`,
not `qwen/qwen3-coder`.

For math formalization specifically, current public theorem-proving papers
point to specialized self-hosted Lean provers rather than general OpenRouter
coder models. `Goedel-Prover-V2-32B` reports 88.1% MiniF2F pass@32 and 90.4%
with self-correction, outperforming prior open-source theorem provers at
release time. `DeepSeek-Prover-V2-671B` reports 88.9% MiniF2F-test pass ratio
and 49/658 PutnamBench problems. Neither appears in the live OpenRouter catalog,
so OpenRouter-only runs should use the current general models while treating
self-hosted specialized provers as the better research target when GPU serving
is available. See `docs/open-model-research-2026-04-28.md`.

## Commands

One built toy tree was reused after disk pressure made duplicate Mathlib checkouts impractical.

```bash
bash examples/toy_project/setup.sh /tmp/repoprover-toy-gemini3-flash
cd /tmp/repoprover-toy-gemini3-flash && lake build
```

Gemini 3 Flash attempt:

```bash
timeout 10m .venv/bin/python -m repoprover run /tmp/repoprover-toy-gemini3-flash \
  --pool-size 1 \
  --provider google \
  --model gemini-3-flash-preview \
  --no-background-agents \
  --verbose
```

OpenRouter GLM 5.1 attempt, historical:

```bash
timeout 12m .venv/bin/python -m repoprover run /tmp/repoprover-toy-gemini3-flash \
  --pool-size 1 \
  --provider openrouter \
  --model z-ai/glm-5.1 \
  --no-background-agents \
  --verbose
```

Current OpenRouter Qwen smoke command:

```bash
timeout 12m .venv/bin/python -m repoprover run /tmp/repoprover-toy-gemini3-flash \
  --pool-size 1 \
  --provider openrouter \
  --model qwen/qwen3.6-35b-a3b \
  --no-background-agents \
  --stop-after-first-merge \
  --verbose
```

## Results

Gemini 3 Flash reached the first tool call, then failed deterministically on the second chat request:

```text
Function call is missing a thought_signature in functionCall parts.
```

The coordinator then relaunched sketchers into the same provider error until the process was killed. Treat this as a provider/transcript compatibility issue, not a Lean or prompt-quality result.

This specific transcript issue is fixed in the shared tool-loop serializer, but the full toy sketch/review/merge path has not yet been rerun with Gemini 3 Flash after the fix.

GLM 5.1 completed the sketch loop. It first wrote a Lean file with an invalid `Even (2 * n)` witness, observed the `lake build` failure, repaired with `lean_check` and Mathlib search, committed the sketch branch, passed review, and merged. The final toy project still builds:

```bash
cd /tmp/repoprover-toy-gemini3-flash && lake build
```

The run was stopped after the sketch merge because the coordinator launched four follow-up maintain contributors for toy target issues. That was enough to validate model/provider/tool/build/review/merge behavior without letting the toy run continue spending tokens.

The successful toy sketch plus both reviewers used 181,115 input tokens and 3,585 output tokens across completed agents. At Gemini 3 Flash Preview standard paid pricing ($0.50/M text input and $3.00/M text output, including reasoning tokens), that same completed first-merge formalization would be about $0.10 before any free-tier credit, taxes, or follow-up maintain agents.

## Learnings File

RepoProver’s code stores generated learnings at:

```text
<lean-project>/.repoprover/learnings.json
```

The toy run did not produce a `learnings.json`. The linked original formalization repository, `facebookresearch/algebraic-combinatorics`, was checked through the GitHub tree API without cloning; no tracked `.repoprover`, `learnings.json`, or similarly named learning file was present. Only `CONTENTS.md` matched the coordination/context search. If such learnings existed during the original run, they were likely generated runtime state outside the published repository.

## Practical Notes

- This machine was disk-bound during the experiments: duplicate toy Mathlib checkouts pushed `/` near full. Reuse one built toy tree or delete old `/tmp/repoprover-toy-*` directories before starting another clean run.
- `--no-background-agents` disables periodic scan/triage/progress agents. For bounded smoke tests, also pass `--stop-after-first-merge` so the coordinator exits after the first successful PR merge instead of launching follow-up maintain/proof contributors.
- For another OpenRouter open-weight attempt, use `qwen/qwen3.6-35b-a3b` first.
  If it regresses on tool use, compare against `deepseek/deepseek-v4-pro`,
  `qwen/qwen3-coder-next`, and `moonshotai/kimi-k2.6`. For self-hosted Lean
  proof generation, prioritize Goedel-Prover-V2 over generic coder models.
