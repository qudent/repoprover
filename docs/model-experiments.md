# RepoProver Toy Model Experiments

This guide records the bounded toy validation runs from April 27, 2026. The goal was not to run a full book proof, but to validate the local RepoProver loop against the toy Lean project.

## Commit Map

- `57421d3` in this repo: baseline local setup, provider/model CLI support, OpenRouter support, and toy Lean build validation.
- `956b452` in this repo: Gemini 3 Flash provider result recorded in `STATUS.md` and `HUMAN_AGENTS_WHITEBOARD.md`.
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

For the current OpenRouter open-weight attempt, `z-ai/glm-5.1` was selected first. Live OpenRouter model metadata described it as a coding model with long-horizon-task gains; it also passed a direct OpenRouter chat smoke. Other reasonable open-weight candidates visible in the same model metadata were `deepseek/deepseek-v4-pro`, `qwen/qwen3-coder`, and `qwen/qwen3-coder-plus`.

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

OpenRouter GLM 5.1 attempt:

```bash
timeout 12m .venv/bin/python -m repoprover run /tmp/repoprover-toy-gemini3-flash \
  --pool-size 1 \
  --provider openrouter \
  --model z-ai/glm-5.1 \
  --no-background-agents \
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
- `--no-background-agents` disables periodic scan/triage/progress agents, but after a sketch merge the coordinator can still launch maintain contributors for target issues. Stop manually once the validation milestone is reached.
- For another open-weight attempt, try `deepseek/deepseek-v4-pro` next if GLM 5.1 regresses; it has a larger context window and passed the direct OpenRouter smoke.
