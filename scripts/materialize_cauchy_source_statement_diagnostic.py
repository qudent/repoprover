#!/usr/bin/env python3
"""Materialize the Cauchy--Binet source-statement diagnostic check.

This is an oracle-assisted diagnostic artifact, not a source-statement
feed-forward benchmark run. It reads the withheld gold declaration from the
local corpus, renames it as a manually repaired generated theorem, appends the
same grader-only `simpa using <generated theorem>` check used by the live eval,
and optionally Lean-checks the resulting project.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.materialize_minimal_context_smoke import SelectedRecord, load_jsonl, read_line_range  # noqa: E402
from scripts.run_source_statement_live_eval import materialize_candidate_project, run_lean  # noqa: E402


DEFAULT_RECORD_ID = (
    "AlgebraicCombinatorics/CauchyBinet.lean:"
    "AlgebraicCombinatorics.CauchyBinet.det_diagonal_submatrix_eq"
)
REPAIRED_NAME = "det_minors_diag_oracle_repair"


def find_record(records_path: Path, record_id: str) -> SelectedRecord:
    for row in load_jsonl(records_path):
        if str(row.get("id") or row.get("record_id")) == record_id:
            return SelectedRecord(row)
    raise ValueError(f"record not found: {record_id}")


def renamed_gold_declaration(project_root: Path, record: SelectedRecord, repaired_name: str) -> str:
    original = read_line_range(project_root / record.lean_path, record.line_range)
    return re.sub(
        r"(\b(?:theorem|lemma)\s+)([^\s:\{\(\[]+)",
        rf"\1{repaired_name}",
        original,
        count=1,
    )


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--records",
        type=Path,
        default=REPO_ROOT / "docs/minimal-context-splits/oracle_source_statement.jsonl",
    )
    parser.add_argument("--project-root", type=Path, default=REPO_ROOT / "algebraic-combinatorics")
    parser.add_argument("--record-id", default=DEFAULT_RECORD_ID)
    parser.add_argument("--output", type=Path, default=Path("/tmp/repoprover-cauchy-source-statement-diagnostic"))
    parser.add_argument(
        "--lake-cache-from",
        type=Path,
        default=None,
        help="Existing project root containing .lake/packages to symlink into the diagnostic project.",
    )
    parser.add_argument("--lean-timeout", type=int, default=90)
    parser.add_argument("--no-lean", action="store_true", help="Only materialize files; do not run Lean.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    record = find_record(args.records, args.record_id)
    repaired = renamed_gold_declaration(args.project_root, record, REPAIRED_NAME)
    target_path = materialize_candidate_project(
        project_root=args.project_root,
        output_root=args.output,
        record=record,
        lean_declaration=repaired,
        generated_name=REPAIRED_NAME,
        lake_cache_from=args.lake_cache_from,
    )
    lean_result: dict[str, Any] | None = None
    if not args.no_lean:
        lean_result = run_lean(args.output, target_path, args.lean_timeout)

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "diagnostic_kind": "manual_oracle_assisted_repair",
        "benchmark_success_claim": False,
        "record_id": record.record_id,
        "source_report": "docs/source-statement-live-eval-report.md",
        "raw_source_statement_output_recovered": False,
        "raw_source_statement_output_note": (
            "This script does not recover the original DeepSeek source-statement generated Lean. "
            "The repository report records only the returned theorem name and key Lean errors."
        ),
        "gold_line_range": list(record.line_range),
        "gold_lean_path": record.lean_path,
        "manual_repaired_generated_name": REPAIRED_NAME,
        "grader_check_criterion": f"by\n  simpa using {REPAIRED_NAME}",
        "materialized_project": str(args.output),
        "materialized_target": str(target_path),
        "lean_check": lean_result,
    }
    write_json(args.output / "diagnostic-summary.json", summary)
    if lean_result is not None and int(lean_result.get("exit_code", 1)) != 0:
        return int(lean_result.get("exit_code", 1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
