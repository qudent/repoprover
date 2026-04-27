# RepoProver - Status

## Current State
RepoProver is installed locally in `.venv`, and Lean/Lake are installed through `elan`. Clean toy Lean projects fetch Mathlib and build successfully with `lake build`; model-provider validation is still in progress.

## Active Goals
- [x] Install local Python and Lean dependencies.
- [x] Validate the toy Lean project setup and build.
- [ ] Get the full toy RepoProver agent run to completion with a reliable model/prompt path.

## Blockers
- The Google `gemini-2.5-flash` toy RepoProver run reaches real LLM/tool/build execution, but the sketcher repeatedly chooses nonexistent Nat parity imports and can hit the agent iteration limit without emitting a completion marker.
- Google `gemini-3-flash-preview` accepts a direct chat smoke, but the OpenAI-compatible tool loop fails after the first tool call with `Function call is missing a thought_signature`; this appears specific to Gemini 3 tool-call continuation through the current OpenAI-style transcript.

## Recent Results
- Created `.venv` with `uv` and installed RepoProver in editable mode.
- Installed `elan`; the toy setup fetched Lean `v4.28.0`, Mathlib, REPL, and completed `lake build`.
- Added CLI provider/model configuration, OpenRouter support, `--no-background-agents`, and passed focused tests.
- Tried a clean toy run at `/tmp/repoprover-toy-gemini3-flash` with `--provider google --model gemini-3-flash-preview`; it failed deterministically on the Gemini thought-signature requirement before any Lean edit could be tested.

## Next Steps
- Try the toy run with a current OpenRouter open-weight coding/reasoning model.
- If model attempts fail, fetch the original formalization context, especially any `.repoprover/learnings.json` or equivalent agent-generated learnings.
- Consider adding a bounded smoke-test command that validates coordinator startup without requiring a full LLM proof loop.
