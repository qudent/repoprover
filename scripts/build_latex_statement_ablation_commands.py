#!/usr/bin/env python3
"""Build budget or paid commands for theorem-level model ablations."""

from __future__ import annotations

import argparse
import json
import shlex
from pathlib import Path
from typing import Any


DEFAULT_CONFIG = Path("configs/latex-statement-model-ablation-2026-05-06.json")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def shell_join(command: list[str]) -> str:
    return shlex.join(command)


def ref(mapping: dict[str, str], value: str) -> str:
    return mapping.get(value, value)


def maybe_add_reasoning(command: list[str], option: str, value: str | None) -> None:
    if value and value != "default":
        command.extend([option, value])


def max_tokens_for(run: dict[str, Any], defaults: dict[str, Any]) -> str:
    return str(run.get("max_tokens") or defaults.get("max_tokens") or 8192)


def add_common_panel_flags(command: list[str], defaults: dict[str, Any]) -> None:
    if defaults.get("materialize_visible_support"):
        command.append("--materialize-visible-support")
        command.extend(["--support-mode", str(defaults.get("support_mode") or "body")])
    if defaults.get("semantic_coverage"):
        command.append("--semantic-coverage")


def panel_output(defaults: dict[str, Any], run_id: str, mode: str) -> str:
    return str(Path(str(defaults.get("output_root") or "docs/latex-statement-ablation-runs")) / mode / run_id)


def build_panel_selector_command(run: dict[str, Any], config: dict[str, Any], mode: str) -> list[str]:
    defaults = config.get("defaults") or {}
    panels = config.get("panels") or {}
    command = [
        "uv",
        "run",
        "python",
        "scripts/run_latex_statement_panel.py",
        "--panel",
        ref(panels, str(run["panel"])),
        "--output",
        panel_output(defaults, str(run["id"]), mode),
        "--selector-model",
        str(run["selector_model"]),
        "--selector-max-tokens",
        max_tokens_for(run, defaults),
        "--selector-temperature",
        str(defaults.get("temperature") or 0.0),
        "--skip-generation",
    ]
    maybe_add_reasoning(command, "--selector-reasoning-effort", run.get("selector_reasoning_effort"))
    if mode == "budget":
        command.append("--selector-budget-only")
    return command


def build_panel_generation_command(run: dict[str, Any], config: dict[str, Any], mode: str) -> list[str]:
    defaults = config.get("defaults") or {}
    panels = config.get("panels") or {}
    selector_runs = config.get("fixed_selector_runs") or {}
    command = [
        "uv",
        "run",
        "python",
        "scripts/run_latex_statement_panel.py",
        "--panel",
        ref(panels, str(run["panel"])),
        "--output",
        panel_output(defaults, str(run["id"]), mode),
        "--selector-run",
        ref(selector_runs, str(run["selector_run"])),
        "--generation-model",
        str(run["generation_model"]),
        "--generation-max-tokens",
        max_tokens_for(run, defaults),
        "--generation-temperature",
        str(defaults.get("temperature") or 0.0),
        "--max-units-per-call",
        str(defaults.get("max_units_per_call") or 1),
    ]
    maybe_add_reasoning(command, "--generation-reasoning-effort", run.get("generation_reasoning_effort"))
    if mode == "budget":
        command.append("--generation-budget-only")
    add_common_panel_flags(command, defaults)
    return command


def build_proof_lane_command(run: dict[str, Any], config: dict[str, Any], mode: str) -> list[str]:
    defaults = config.get("defaults") or {}
    task_dirs = config.get("proof_lane_task_dirs") or {}
    command = [
        "uv",
        "run",
        "python",
        "scripts/run_latex_statement_proof_lane_generation.py",
        "--proof-lane-task-dir",
        ref(task_dirs, str(run["proof_lane_task_dir"])),
        "--output",
        panel_output(defaults, str(run["id"]), mode),
        "--model",
        str(run["model"]),
        "--max-tasks-per-call",
        "1",
        "--max-tokens",
        max_tokens_for(run, defaults),
        "--temperature",
        str(defaults.get("temperature") or 0.0),
        "--resume-existing",
    ]
    maybe_add_reasoning(command, "--reasoning-effort", run.get("reasoning_effort"))
    if mode == "budget":
        command.append("--budget-only")
    return command


def build_command(run: dict[str, Any], config: dict[str, Any], mode: str) -> list[str]:
    kind = run.get("kind")
    if kind == "panel_selector_context":
        return build_panel_selector_command(run, config, mode)
    if kind == "panel_generation_fixed_selector":
        return build_panel_generation_command(run, config, mode)
    if kind == "proof_lane_generation":
        return build_proof_lane_command(run, config, mode)
    raise ValueError(f"unsupported ablation kind: {kind}")


def build_rows(config: dict[str, Any], mode: str, run_ids: set[str] | None = None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for run in config.get("runs") or []:
        run_id = str(run.get("id") or "")
        if run_ids and run_id not in run_ids:
            continue
        command = build_command(run, config, mode)
        rows.append(
            {
                "id": run_id,
                "kind": run.get("kind"),
                "mode": mode,
                "why": run.get("why"),
                "command": command,
                "shell": shell_join(command),
            }
        )
    return rows


def render_markdown(rows: list[dict[str, Any]]) -> str:
    lines = ["# LaTeX Statement Ablation Commands", "", "| ID | Kind | Mode | Command |", "|---|---|---|---|"]
    for row in rows:
        lines.append(f"| `{row['id']}` | `{row['kind']}` | `{row['mode']}` | `{row['shell']}` |")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--mode", choices=["budget", "paid"], default="budget")
    parser.add_argument("--run-id", action="append", help="Limit output to one ablation id; may be repeated.")
    parser.add_argument("--format", choices=["shell", "json", "markdown"], default="shell")
    args = parser.parse_args()
    config = read_json(args.config)
    rows = build_rows(config, args.mode, set(args.run_id or []) or None)
    if args.format == "json":
        print(json.dumps({"config": str(args.config), "mode": args.mode, "runs": rows}, indent=2, sort_keys=True))
    elif args.format == "markdown":
        print(render_markdown(rows))
    else:
        for row in rows:
            print(f"# {row['id']}: {row.get('why') or ''}".rstrip())
            print(row["shell"])


if __name__ == "__main__":
    main()
