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
