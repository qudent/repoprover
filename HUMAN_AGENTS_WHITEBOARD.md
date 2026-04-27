# RepoProver - Human/Agents Whiteboard

## Active Human Prompts
- Try the toy example with Gemini 3 Flash, then the current best OpenRouter open-weight model for Lean/code/tool work. If that does not work, download relevant original-repo context and check whether agent-generated learnings exist. Commit along the way and write a concise experiment guide linking relevant commits.

## Agent Notes
- Local install is complete. Toy Lean setup/build succeeds at `/tmp/repoprover-toy-test`.
- RepoProver reaches real LLM/tool/build execution on the toy project with `--provider google --no-background-agents`, but Gemini did not complete the sketch cleanly in the latest run.
- Run logs are under `/tmp/repoprover-toy-test/runs/20260427-164853/`.
- A clean `gemini-3-flash-preview` toy attempt was created at `/tmp/repoprover-toy-gemini3-flash`; the model ID works for direct chat, but the agent run failed immediately because Gemini 3 requires tool-call `thought_signature` data that the current OpenAI-compatible message replay does not preserve.

## Open Questions
- Whether the OpenRouter open-weight attempt completes without prompt/tool-loop changes.
