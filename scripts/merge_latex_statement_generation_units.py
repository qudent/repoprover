#!/usr/bin/env python3
"""Overlay targeted theorem-level generation outputs onto a base run."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.run_latex_statement_generation import read_json, write_json  # noqa: E402
from scripts.run_latex_statement_generation_repair import load_generation_output  # noqa: E402


def generation_output_paths(run_dir: Path) -> list[Path]:
    if run_dir.is_file():
        return [run_dir]
    return sorted(run_dir.glob("batch-*/generation-output.json"))


def payload_path_for_unit(run_dir: Path, unit_key: str) -> Path | None:
    for output_path in generation_output_paths(run_dir):
        try:
            output = read_json(output_path)
        except (OSError, json.JSONDecodeError):
            continue
        if any(str(unit.get("unit_key") or "") == unit_key for unit in output.get("units") or []):
            payload_path = output_path.parent / "generation-payload.json"
            if payload_path.exists():
                return payload_path
    fallback = run_dir / "batch-001" / "generation-payload.json"
    return fallback if fallback.exists() else None


def overlay_units(base_units: list[dict[str, Any]], overlays: list[dict[str, Any]]) -> list[dict[str, Any]]:
    overlay_by_key: dict[str, dict[str, Any]] = {}
    for overlay in overlays:
        for unit in overlay.get("units") or []:
            unit_key = str(unit.get("unit_key") or "")
            if unit_key:
                overlay_by_key[unit_key] = unit

    merged: list[dict[str, Any]] = []
    seen: set[str] = set()
    for unit in base_units:
        unit_key = str(unit.get("unit_key") or "")
        merged.append(overlay_by_key.get(unit_key, unit))
        seen.add(unit_key)
    for unit_key, unit in overlay_by_key.items():
        if unit_key not in seen:
            merged.append(unit)
    return merged


def run_results(run_dir: Path) -> dict[str, Any]:
    if run_dir.is_file():
        return {}
    for name in ("generation-results.json", "repair-results.json"):
        path = run_dir / "eval" / name
        if path.exists():
            try:
                return read_json(path)
            except (OSError, json.JSONDecodeError):
                return {}
    return {}


def run(args: argparse.Namespace) -> dict[str, Any]:
    args.output.mkdir(parents=True, exist_ok=True)
    eval_dir = args.output / "eval"
    eval_dir.mkdir(exist_ok=True)

    base_output = load_generation_output(args.base_generation_run)
    base_results = run_results(args.base_generation_run)
    overlay_outputs = [load_generation_output(path) for path in args.overlay_generation_run]
    merged_units = overlay_units(base_output.get("units") or [], overlay_outputs)
    merged_output = {
        "schema_version": "repoprover.latex_statement_generation_overlay.v1",
        "base_generation_run": str(args.base_generation_run),
        "overlay_generation_runs": [str(path) for path in args.overlay_generation_run],
        "units": merged_units,
    }
    write_json(eval_dir / "merged-generation-output.json", merged_output)

    payload_sources: list[dict[str, str]] = []
    overlay_unit_keys = {
        str(unit.get("unit_key") or "")
        for output in overlay_outputs
        for unit in output.get("units") or []
        if unit.get("unit_key")
    }
    for index, unit in enumerate(merged_units, start=1):
        unit_key = str(unit.get("unit_key") or "")
        batch_dir = args.output / f"batch-{index:03d}"
        batch_output = {**merged_output, "units": [unit]}
        for name in ("generation-output.json", "repair-output.json"):
            write_json(batch_dir / name, batch_output)
        source_run = next(
            (
                overlay_run
                for overlay_run in args.overlay_generation_run
                if unit_key
                in {
                    str(row.get("unit_key") or "")
                    for row in load_generation_output(overlay_run).get("units") or []
                }
            ),
            args.base_generation_run,
        )
        payload_source = payload_path_for_unit(source_run, unit_key)
        if payload_source is not None:
            payload_target = batch_dir / "generation-payload.json"
            write_json(payload_target, read_json(payload_source))
            payload_sources.append(
                {
                    "unit_key": unit_key,
                    "payload_source": str(payload_source),
                    "payload_target": str(payload_target),
                }
            )

    summary = {
        "schema_version": "repoprover.latex_statement_generation_overlay_run.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "base_generation_run": str(args.base_generation_run),
        "overlay_generation_runs": [str(path) for path in args.overlay_generation_run],
        "overlay_unit_keys": sorted(overlay_unit_keys),
        "unit_count": len(merged_units),
        "output": str(args.output),
        "merged_generation_output": str(eval_dir / "merged-generation-output.json"),
        "selector_run": base_results.get("selector_run"),
        "model": base_results.get("model"),
        "reasoning_effort": base_results.get("reasoning_effort"),
        "paid_call_made": False,
        "payload_sources": payload_sources,
    }
    write_json(eval_dir / "generation-results.json", summary)
    write_json(eval_dir / "repair-results.json", summary)
    write_json(eval_dir / "merge-summary.json", summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-generation-run", type=Path, required=True)
    parser.add_argument("--overlay-generation-run", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
