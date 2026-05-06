#!/usr/bin/env python3
"""Normalize existing theorem-level generation or repair outputs.

This is a no-provider-call utility. It applies the same benchmark-honesty
contract enforcement used by live generation/repair runners to an already
recorded run, preserving raw model output while writing normalized
``generation-output.json`` / ``repair-output.json`` files in a new run
directory.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.run_latex_statement_generation import enforce_generation_contracts, read_json, write_json


def batch_dirs(run_dir: Path) -> list[Path]:
    if run_dir.is_file():
        return [run_dir.parent]
    return sorted(path for path in run_dir.glob("batch-*") if path.is_dir())


def copy_batch_inputs(source_batch: Path, output_batch: Path) -> None:
    output_batch.mkdir(parents=True, exist_ok=True)
    for path in source_batch.iterdir():
        if path.is_dir():
            shutil.copytree(path, output_batch / path.name, dirs_exist_ok=True)
        else:
            shutil.copy2(path, output_batch / path.name)


def normalize_output_file(output_path: Path, *, raw_name: str) -> dict[str, Any] | None:
    if not output_path.exists():
        return None
    original = read_json(output_path)
    normalized, report = enforce_generation_contracts(original)
    if report["normalized_unit_count"]:
        write_json(output_path.with_name(raw_name), original)
        write_json(output_path, normalized)
    return {
        "output": str(output_path),
        "raw_output": str(output_path.with_name(raw_name)) if report["normalized_unit_count"] else None,
        **report,
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    source_run = args.generation_run
    output_run = args.output
    output_run.mkdir(parents=True, exist_ok=True)
    summaries: list[dict[str, Any]] = []
    for source_batch in batch_dirs(source_run):
        batch_name = source_batch.name if source_batch.name.startswith("batch-") else "batch-001"
        output_batch = output_run / batch_name
        copy_batch_inputs(source_batch, output_batch)
        generation_summary = normalize_output_file(
            output_batch / "generation-output.json",
            raw_name="raw-generation-output.json",
        )
        repair_summary = normalize_output_file(
            output_batch / "repair-output.json",
            raw_name="raw-repair-output.json",
        )
        summaries.append(
            {
                "batch": batch_name,
                "generation": generation_summary,
                "repair": repair_summary,
            }
        )

    summary = {
        "schema_version": "repoprover.latex_statement_generation_normalization.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_run": str(source_run),
        "output_run": str(output_run),
        "paid_call_made": False,
        "batches": summaries,
    }
    write_json(output_run / "eval" / "normalization-results.json", summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--generation-run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
