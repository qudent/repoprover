# RepoProver - Status

## Current State
RepoProver is installed locally in `.venv`, and Lean/Lake are installed through `elan`. The toy Lean project validates with OpenRouter `z-ai/glm-5.1` through sketch, review, merge, and final `lake build`.

## Active Goals
- [x] Install local Python and Lean dependencies.
- [x] Validate the toy Lean project setup and build.
- [x] Get the toy RepoProver sketch/review/merge loop to completion with a reliable model/provider path.
- [x] Document model experiments and relevant commit hashes.

## Blockers
- The Google `gemini-2.5-flash` toy RepoProver run reaches real LLM/tool/build execution, but the sketcher repeatedly chooses nonexistent Nat parity imports and can hit the agent iteration limit without emitting a completion marker.
- Google `gemini-3-flash-preview` accepts a direct chat smoke, but the OpenAI-compatible tool loop fails after the first tool call with `Function call is missing a thought_signature`; this appears specific to Gemini 3 tool-call continuation through the current OpenAI-style transcript.

## Recent Results
- Created `.venv` with `uv` and installed RepoProver in editable mode.
- Installed `elan`; the toy setup fetched Lean `v4.28.0`, Mathlib, REPL, and completed `lake build`.
- Added CLI provider/model configuration, OpenRouter support, `--no-background-agents`, and passed focused tests.
- Tried a clean toy run at `/tmp/repoprover-toy-gemini3-flash` with `--provider google --model gemini-3-flash-preview`; it failed deterministically on the Gemini thought-signature requirement before any Lean edit could be tested.
- Reused the built toy tree for `--provider openrouter --model z-ai/glm-5.1`; GLM 5.1 created, repaired, reviewed, and merged the toy sketch. Toy commits: `97c3bd9` sketch, `ed17e510` merge, `eef1daf` generated follow-up issues.
- Checked `facebookresearch/algebraic-combinatorics` via the GitHub tree API; no tracked `.repoprover/learnings.json` or similar learnings file exists in the published repo.

## Next Steps
- If continuing the toy proof loop, resume from `/tmp/repoprover-toy-gemini3-flash` after cleaning orphan maintain worktrees or start a fresh tree after freeing disk.
- Consider adding a CLI stop condition that exits after first successful sketch merge to make this smoke test bounded.
