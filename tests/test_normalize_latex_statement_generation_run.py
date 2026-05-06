"""Tests for no-cost theorem-level generation output normalization."""

import argparse
import json
from pathlib import Path

from scripts.normalize_latex_statement_generation_run import run


def test_normalize_generation_run_preserves_raw_and_writes_empty_decline(tmp_path: Path) -> None:
    source = tmp_path / "source-run"
    batch = source / "batch-001"
    batch.mkdir(parents=True)
    (batch / "generation-payload.json").write_text("{}", encoding="utf-8")
    (batch / "generation-output.json").write_text(
        json.dumps(
            {
                "units": [
                    {
                        "unit_key": "unit-001",
                        "status": "generated",
                        "lean_file_body": "theorem bad : True := by\n  -- incomplete\n  sorry",
                        "declaration_names": ["bad"],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    output = tmp_path / "normalized-run"

    summary = run(argparse.Namespace(generation_run=source, output=output))

    normalized = json.loads((output / "batch-001/generation-output.json").read_text(encoding="utf-8"))
    raw = json.loads((output / "batch-001/raw-generation-output.json").read_text(encoding="utf-8"))

    assert summary["paid_call_made"] is False
    assert summary["batches"][0]["generation"]["normalized_unit_count"] == 1
    assert normalized["units"][0]["status"] == "cannot_prove_from_visible_context"
    assert normalized["units"][0]["lean_file_body"] == ""
    assert normalized["units"][0]["declaration_names"] == []
    assert raw["units"][0]["lean_file_body"].startswith("theorem bad")
    assert (output / "eval/normalization-results.json").exists()
