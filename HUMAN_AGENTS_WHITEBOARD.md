# RepoProver - Human/Agents Whiteboard

## Active Human Prompts
## General strategy
 - from the extant completed formalization, build a gold standard "minimal context" set: Given this formalization, look at all the chunks of the output formalization (lemmata etc, or just chunks of text) and look at the smallest set of context (in the original textbook, and the definitions/proofs preceding it, and the lean defs/proofs) necessary to formalize it (and use the exact syntax chosen for the formalizes ancestor defs)
- iterate on getting the gold standard sets right with open/cheap models
- track trust scores of all agent-generated things and inputs (and also trust score of completeness of dependency graph itself); if agents continue failing, reduce trust score of ancestors in dependency graph until one does a more thorough review with a better agent/the context of failure
## Plan
- How far can we get with 50 $ in compute? Make a plan. Maybe first formalize the first few pages of the thing, and generate a set based on that? Please do some estimates how much this will take on openrouter in a reasonable number of rounds. I have 10 $ on the API key now, show me how far you get with that money and 6 hours, do planning. Commit intermediate steps and write a concise report of your choices and learnings.

## Agent Notes
- Local install is complete. Toy Lean setup/build succeeds at `/tmp/repoprover-toy-test`.
- RepoProver reaches real LLM/tool/build execution on the toy project with `--provider google --no-background-agents`, but Gemini did not complete the sketch cleanly in the latest run.
- Run logs are under `/tmp/repoprover-toy-test/runs/20260427-164853/`.
- A clean `gemini-3-flash-preview` toy attempt was created at `/tmp/repoprover-toy-gemini3-flash`; the model ID works for direct chat. The OpenAI-compatible tool loop now preserves provider-specific tool-call metadata, including Gemini thought signatures, and a live one-tool continuation smoke passes.
- OpenRouter `z-ai/glm-5.1` succeeded through the bounded toy sketch/review/merge path in `/tmp/repoprover-toy-gemini3-flash`; final `lake build` passes. The run was stopped after the coordinator launched follow-up maintain contributors.
- Pricing estimate for the first-merge toy formalization is about $0.10 on Gemini 3 Flash Preview standard paid pricing, based on completed sketch plus two reviewer token totals.
- Experiment guide: `docs/model-experiments.md`.

## Open Questions
- Should RepoProver grow a first-merge smoke-test stop condition to avoid manually killing follow-up maintain/proof agents?
  - what do you mean with that? elaborate?
