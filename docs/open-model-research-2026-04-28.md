# Open Model Research - 2026-04-28

This note records the model refresh behind the April 28 RepoProver
minimal-context rerun. The key correction is that `qwen/qwen3-coder` is now a
historical model choice for this repo, not the current Qwen default.

## Current Catalog Findings

- Qwen upstream: the official Qwen3.6 repository says Qwen3.6 is the latest
  Qwen family addition, with Qwen3.6-35B-A3B released on 2026-04-16 and
  Qwen3.6-27B released on 2026-04-22. It also states that open-weight models
  are Apache 2.0 licensed.
- OpenRouter: the live catalog currently includes `qwen/qwen3.6-35b-a3b`,
  `qwen/qwen3.6-27b`, `qwen/qwen3.6-plus`,
  `qwen/qwen3.6-flash`, and `qwen/qwen3.6-max-preview`. It also still includes
  older `qwen/qwen3-coder`, `qwen/qwen3-coder-next`, and Qwen3.5 models.
- Repo default for OpenRouter minimal-context JSON generation/review is now
  `qwen/qwen3.6-35b-a3b`, because it is current and open-weight. Use
  `--reasoning-effort none` for schema-bound JSON jobs; without it, both
  Qwen3.6-35B-A3B and Qwen3.6-27B returned empty content on the first
  generation request.

## Formalization-Specific Finding

OpenRouter does not currently list specialized Lean provers such as
Goedel-Prover-V2 or DeepSeek-Prover-V2. For OpenRouter-only experiments, the
best available open-weight choices are therefore current general coding or
reasoning models, not theorem-prover-specialized models.

For self-hosting, the literature points away from generic coder models:

- DeepSeek-Prover-V2 is an open-source Lean 4 theorem-proving model and reports
  88.9% pass ratio on MiniF2F-test, plus 49/658 PutnamBench problems.
- Goedel-Prover-V2 reports stronger constrained-compute open-source theorem
  proving: the 32B model reaches 88.1% MiniF2F pass@32, 90.4% with
  self-correction, and leads PutnamBench among open-source models at the time
  of release.

Practical implication: use `qwen/qwen3.6-35b-a3b` for cheap OpenRouter
minimal-context generation/review now, but treat `Goedel-Prover-V2-32B` as the
more relevant self-hosted candidate for Lean proof generation if GPU serving is
available.

## Repo Changes From This Refresh

- `scripts/generate_minimal_context_records.py` default model:
  `qwen/qwen3.6-35b-a3b`.
- `scripts/review_minimal_context_records.py` default model:
  `qwen/qwen3.6-35b-a3b`.
- Both scripts now accept `--reasoning-effort`; for the Qwen3.6 JSON run,
  `--reasoning-effort none` was required.
- `scripts/estimate_openrouter_budget.py` default comparison set now includes
  current Qwen3.6, Qwen Coder Next, Kimi K2.6, DeepSeek V4 Pro, GLM 5.1, and
  Gemini Flash.
- New rerun artifacts:
  - `docs/minimal-context-generated-records-batch2-qwen3.6-35b-a3b.jsonl`
  - `docs/minimal-context-generated-review-batch2-qwen3.6-35b-a3b.jsonl`
  - `docs/minimal-context-generated-review-batch2-qwen3.6-35b-a3b-report.md`

## Sources

- Qwen3.6 official repository: https://github.com/QwenLM/Qwen3.6
- OpenRouter live model catalog: https://openrouter.ai/api/v1/models
- OpenRouter reasoning parameters: https://openrouter.ai/docs/use-cases/reasoning-tokens
- DeepSeek-Prover-V2 paper: https://arxiv.org/abs/2504.21801
- Goedel-Prover-V2 paper: https://arxiv.org/abs/2508.03613
- Goedel-Prover-V2 repository: https://github.com/Goedel-LM/Goedel-Prover-V2
