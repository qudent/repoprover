# RepoProver - Status

## Current State
RepoProver is installed locally in `.venv`, and Lean/Lake are installed through `elan`. The toy Lean project at `/tmp/repoprover-toy-test` has fetched Mathlib and builds successfully with `lake build`.

## Active Goals
- [x] Install local Python and Lean dependencies.
- [x] Validate the toy Lean project setup and build.
- [ ] Get the full toy RepoProver agent run to completion with a reliable model/prompt path.

## Blockers
- The Google `gemini-2.5-flash` toy RepoProver run reaches real LLM/tool/build execution, but the sketcher repeatedly chooses nonexistent Nat parity imports and can hit the agent iteration limit without emitting a completion marker.

## Recent Results
- Created `.venv` with `uv` and installed RepoProver in editable mode.
- Installed `elan`; the toy setup fetched Lean `v4.28.0`, Mathlib, REPL, and completed `lake build`.
- Added CLI provider/model configuration, OpenRouter support, `--no-background-agents`, and passed focused tests.

## Next Steps
- Try the toy run with a stronger model or tune the sketch prompt for the toy parity target.
- Consider adding a bounded smoke-test command that validates coordinator startup without requiring a full LLM proof loop.
