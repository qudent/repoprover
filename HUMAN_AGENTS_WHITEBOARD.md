# RepoProver - Human/Agents Whiteboard

## Active Human Prompts
- Get RepoProver running locally. Do not start a whole-book proof; validate only with the toy example.

## Agent Notes
- Local install is complete. Toy Lean setup/build succeeds at `/tmp/repoprover-toy-test`.
- RepoProver reaches real LLM/tool/build execution on the toy project with `--provider google --no-background-agents`, but Gemini did not complete the sketch cleanly in the latest run.
- Run logs are under `/tmp/repoprover-toy-test/runs/20260427-164853/`.

## Open Questions
- Which model should be used for a stronger toy completion attempt if `gemini-2.5-flash` remains unreliable?
