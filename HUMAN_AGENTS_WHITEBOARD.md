# RepoProver - Human/Agents Whiteboard

## Active Human Prompts
- None.

## Agent Notes
- Local install is complete. Toy Lean setup/build succeeds at `/tmp/repoprover-toy-test`.
- RepoProver reaches real LLM/tool/build execution on the toy project with `--provider google --no-background-agents`, but Gemini did not complete the sketch cleanly in the latest run.
- Run logs are under `/tmp/repoprover-toy-test/runs/20260427-164853/`.
- A clean `gemini-3-flash-preview` toy attempt was created at `/tmp/repoprover-toy-gemini3-flash`; the model ID works for direct chat, but the agent run failed immediately because Gemini 3 requires tool-call `thought_signature` data that the current OpenAI-compatible message replay does not preserve.
- OpenRouter `z-ai/glm-5.1` succeeded through the bounded toy sketch/review/merge path in `/tmp/repoprover-toy-gemini3-flash`; final `lake build` passes. The run was stopped after the coordinator launched follow-up maintain contributors.
- Experiment guide: `docs/model-experiments.md`.

## Open Questions
- Should RepoProver grow a first-merge smoke-test stop condition to avoid manually killing follow-up maintain/proof agents?
