# Repository Guidelines

## Project Structure & Module Organization

RepoProver is a Python package under `src/repoprover/`. Core orchestration lives
in `coordinator.py`, CLI entrypoints in `cli.py` and `__main__.py`, shared build
and Lean helpers in `build.py`, `lean_checker.py`, and `lean_utils.py`, and agent
tooling in `src/repoprover/agents/`. Tests mirror this surface in `tests/`.

Use `scripts/` for one-off analysis and benchmark utilities, `configs/` for
example manifests, `docs/` for architecture notes and experiment artifacts, and
`examples/toy_project/` for local Lean smoke tests. Keep generated run state out
of the repo unless it is an intentional benchmark artifact.

## Build, Test, and Development Commands

- `uv sync` installs the package and dependencies from `pyproject.toml` and
  `uv.lock`.
- `uv run pytest` runs the Python test suite.
- `uv run python -m repoprover --help` checks the CLI entrypoint.
- `bash examples/toy_project/setup.sh /tmp/repoprover-toy-test` prepares the
  Lean toy project.
- `uv run python -m repoprover run /tmp/repoprover-toy-test --pool-size 1 --stop-after-first-merge`
  runs a bounded local smoke after the toy setup.

For Lean build behavior, prefer the centralized helpers in `repoprover.build`
instead of direct `subprocess.run(["lake", "build"])` calls.

## Coding Style & Naming Conventions

Write Python 3.10+ with type annotations where they clarify interfaces. Follow
the existing style: 4-space indentation, `snake_case` functions and modules,
`PascalCase` classes, dataclasses for structured task/result data, and explicit
`Path` handling for filesystem work. Keep public agent tools small and register
tool handlers by the existing `_handle_{tool_name}` convention.

## Testing Guidelines

Tests use `pytest`; add or update focused tests in `tests/test_*.py` for behavior
changes. Prefer fake clients and toy projects for deterministic unit coverage.
Run `uv run pytest` before submitting, and add a toy Lean smoke when changes
touch coordinator, build, Lean, provider, or worktree behavior.

## Commit & Pull Request Guidelines

Recent history uses short imperative or outcome-oriented subjects, for example
`Add minimal-context record generator` or `finished: codex exec "..."`
autosaves. Make each commit one coherent unit and include generated benchmark
artifacts only when they are reviewable inputs or results.

Pull requests should describe the change, list tests or smoke runs performed,
link related issues when available, and call out provider/API-key assumptions or
OpenRouter spend for live LLM experiments. Update docs when APIs, commands, or
benchmark formats change.

## Agent-Specific Notes

Read `STATUS.md` before non-trivial work and rewrite it after meaningful state
changes. Keep project-specific commands and current plans there or in `docs/`,
not in global learnings. Preserve hard benchmark examples; do not silently drop
ugly or failing records.

## Theorem-Level Pipeline Discipline

For LaTeX-statement autoformalization work, implement the report recommendations
rather than only summarizing them:

- Before another paid one-off retry, inspect recent `STATUS.md` history and the
  latest `reports/REPORT-*.md` files for repeated loops or stale assumptions.
- Prefer frozen panels over single-theorem optimization. Use
  `docs/latex-statement-dev-panel-2026-05-06.json` for contaminated development
  feedback and `docs/latex-statement-fresh-slice-2026-05-06.json` as the current
  reserve/fresh check. Do not call a prompt or context rule generic until it has
  been scored outside the theorem that induced it.
- Keep DeepSeek V4 Flash as the cheap selector/context baseline, but do not
  assume it is the proof-lane winner. Use
  `configs/latex-statement-model-ablation-2026-05-06.json` and
  `scripts/build_latex_statement_ablation_commands.py` to compare Flash, V4 Pro,
  Kimi K2.6, and GPT-5.5 on identical panels/task dirs before more one-off
  proof-lane retries. "Top-line" proof-lane probes should use the strongest
  supported reasoning setting and a large completion budget, not the cheap
  no-reasoning defaults.
- Emit budget/dry-run payloads first when changing prompts, context hydration,
  or model mix. Inspect payloads for target leakage and fake context before paid
  calls.
- Record paid or acceptance-bearing runs with
  `scripts/update_latex_statement_run_ledger.py` into
  `docs/latex-statement-run-ledger.jsonl`. The ledger should include artifact
  root, units, model/reasoning, cost/tokens, context counts, compile/semantic
  counts, failure classes, and the verification artifact path. If Lean import
  setup takes close to the verifier timeout, rerun with a larger timeout and do
  not keep stale timeout artifacts as the headline result.
- When resuming a paid generation after invalid JSON, provider failure, or
  contract normalization, preserve the previous paid attempt and its cost. Do
  not let a successful retry overwrite the only durable record of money already
  spent.
- Use an explicit provider request timeout for high-reasoning or large-token
  OpenRouter calls. If a provider returns reasoning-only/null content or hangs,
  log the paid response/interruption as an artifact before retrying with changed
  settings.
- After two attempts on the same unit with the same failure class and adequate
  checked context, stop prompt/context tuning and route the case to a different
  lane: stronger-model ablation, manual Lean lemma development, Mathlib/project
  API lookup, or a proof-synthesis worker.
- Treat clean `cannot_prove_from_visible_context` declines as a quality metric,
  not proof progress. Benchmark progress means Lean compilation and post-hoc
  semantic coverage improve under the target-hidden contract.
- Bottom-line viability claims must be evidence-based. Current artifacts do not
  demonstrate a robust path to formalizing 90% of the book for about `$100`;
  they demonstrate useful cheap components plus unresolved proof-lane and
  context-routing blockers.
