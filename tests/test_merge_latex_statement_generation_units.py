"""Tests for overlaying targeted theorem-level generation outputs."""

import argparse
import json
from pathlib import Path

from scripts.merge_latex_statement_generation_units import run


def _write_batch(run_dir: Path, batch: int, unit_key: str, body: str) -> None:
    batch_dir = run_dir / f"batch-{batch:03d}"
    batch_dir.mkdir(parents=True)
    output = {
        "units": [
            {
                "unit_key": unit_key,
                "status": "generated",
                "lean_file_body": body,
                "declaration_names": [body],
            }
        ]
    }
    (batch_dir / "generation-output.json").write_text(json.dumps(output), encoding="utf-8")
    (batch_dir / "generation-payload.json").write_text(
        json.dumps({"payload_for": unit_key}),
        encoding="utf-8",
    )


def test_overlay_targeted_generation_units_preserves_order_and_payloads(tmp_path: Path) -> None:
    base = tmp_path / "base"
    overlay = tmp_path / "overlay"
    _write_batch(base, 1, "unit-001", "base-one")
    _write_batch(base, 2, "unit-002", "base-two")
    _write_batch(overlay, 1, "unit-002", "overlay-two")
    (base / "eval").mkdir()
    (base / "eval/generation-results.json").write_text(
        json.dumps({"selector_run": "selector/path", "model": "model/id"}),
        encoding="utf-8",
    )

    output = tmp_path / "merged"
    summary = run(
        argparse.Namespace(
            base_generation_run=base,
            overlay_generation_run=[overlay],
            output=output,
        )
    )

    merged = json.loads((output / "eval/merged-generation-output.json").read_text(encoding="utf-8"))
    batch_1 = json.loads((output / "batch-001/generation-output.json").read_text(encoding="utf-8"))
    batch_2 = json.loads((output / "batch-002/generation-output.json").read_text(encoding="utf-8"))
    payload_1 = json.loads((output / "batch-001/generation-payload.json").read_text(encoding="utf-8"))
    payload_2 = json.loads((output / "batch-002/generation-payload.json").read_text(encoding="utf-8"))
    results = json.loads((output / "eval/generation-results.json").read_text(encoding="utf-8"))

    assert summary["overlay_unit_keys"] == ["unit-002"]
    assert summary["selector_run"] == "selector/path"
    assert [unit["lean_file_body"] for unit in merged["units"]] == ["base-one", "overlay-two"]
    assert batch_1["units"][0]["unit_key"] == "unit-001"
    assert batch_2["units"][0]["unit_key"] == "unit-002"
    assert payload_1["payload_for"] == "unit-001"
    assert payload_2["payload_for"] == "unit-002"
    assert results["selector_run"] == "selector/path"
    assert results["paid_call_made"] is False


def test_overlay_file_without_payload_falls_back_to_base_unit_payload(tmp_path: Path) -> None:
    base = tmp_path / "base"
    _write_batch(base, 1, "unit-001", "base-one")
    _write_batch(base, 2, "unit-002", "base-two")
    (base / "eval").mkdir()
    (base / "eval/generation-results.json").write_text(
        json.dumps({"selector_run": "selector/path"}),
        encoding="utf-8",
    )
    overlay_file = tmp_path / "proof-lane-solution.json"
    overlay_file.write_text(
        json.dumps(
            {
                "units": [
                    {
                        "unit_key": "unit-002",
                        "status": "generated",
                        "lean_file_body": "overlay-two",
                        "declaration_names": ["overlay_two"],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    output = tmp_path / "merged"
    run(
        argparse.Namespace(
            base_generation_run=base,
            overlay_generation_run=[overlay_file],
            output=output,
        )
    )

    payload_2 = json.loads((output / "batch-002/generation-payload.json").read_text(encoding="utf-8"))

    assert payload_2["payload_for"] == "unit-002"
