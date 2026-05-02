#!/usr/bin/env python3
"""Split RepoProver minimal-context records into leakage-aware benchmark tracks.

The input records in docs/minimal-context-gold-candidates.jsonl are useful, but
some context was selected with knowledge of the target declaration/source label.
This script preserves that oracle track and emits stricter tracks whose metadata
states exactly what is and is not being measured.
"""

from __future__ import annotations

import argparse
import copy
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "repoprover.minimal_context_splits.v1"
TRACKS = ("oracle_proof_fill", "oracle_source_statement", "prefix_next_declaration")

TRACK_METADATA: dict[str, dict[str, str | list[str]]] = {
    "oracle_proof_fill": {
        "leakage_level": "oracle_upper_bound",
        "allowed_context_policy": (
            "May include target-derived TeX/source spans, target-derived Lean file context, "
            "and selected Lean predecessors from the current minimal-context record."
        ),
        "target_policy": "Lean target statement/skeleton is available with proof/body replaced by sorry.",
        "estimated_use": (
            "Upper-bound proof-fill/great-context benchmark. If a system gets 100%, it can fill "
            "proofs when a strong oracle has already selected the relevant statement and context."
        ),
        "limitations": [
            "Not an honest autoformalization benchmark: minimal_context was selected after seeing the target.",
            "May reward using target/source labels and target-shaped Lean context.",
        ],
    },
    "oracle_source_statement": {
        "leakage_level": "source_statement_oracle_prefix_lean",
        "allowed_context_policy": (
            "Selected target TeX/source span may be label-derived, but Lean context is restricted "
            "to imports, file-scope context, and predecessor chunks strictly before the target Lean range."
        ),
        "target_policy": "Target TeX/source chunk is available; target Lean statement should be withheld by consumers.",
        "estimated_use": (
            "Measures formalizing a known next mathematical text chunk into Lean using only prefix Lean dependencies."
        ),
        "limitations": [
            "The source chunk can still be oracle-selected by a Lean comment label.",
            "The JSON record retains output line ranges/declaration names for grading; prompts should not expose a target Lean statement.",
        ],
    },
    "prefix_next_declaration": {
        "leakage_level": "honest_prefix_with_documented_source_alignment_limitations",
        "allowed_context_policy": (
            "Lean context is prefix-only: file context and predecessor chunks must end strictly before the target "
            "in the same Lean file (or be from a lexicographically earlier Lean file when present in the input). "
            "TeX context is a window ending strictly before the aligned target source span; the target source span itself is withheld."
        ),
        "target_policy": "Next declaration identity is for grading only; target Lean statement and target source span should be withheld.",
        "estimated_use": (
            "Closest feed-forward split available from current records: predict the next Lean declaration from prior Lean and prior TeX context."
        ),
        "limitations": [
            "Current records do not contain a full non-oracle TeX cursor, so the prefix TeX window is anchored by the target-aligned source span start.",
            "Because that anchor is target-derived, this is not yet a fully certified feed-forward corpus split.",
            "Only predecessor chunks already present in the input record can be retained; missing true dependencies are not recovered here.",
        ],
    },
}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")


def _target_start(record: dict[str, Any]) -> int:
    return int(record.get("output", {}).get("line_range", [0, 0])[0])


def _target_lean_path(record: dict[str, Any]) -> str:
    return str(record.get("output", {}).get("lean_path", ""))


def ends_before_target(span: dict[str, Any], record: dict[str, Any]) -> bool:
    path = str(span.get("path", ""))
    line_range = span.get("line_range") or [0, 0]
    end = int(line_range[1])
    target_path = _target_lean_path(record)
    if path == target_path:
        return end < _target_start(record)
    # Imported/other-file predecessors in the generated records normally denote
    # dependencies from previous modules. Without a corpus-order index, use a
    # deterministic conservative proxy and document it in metadata.
    return bool(path) and path < target_path


def prefix_only_context(record: dict[str, Any]) -> dict[str, Any]:
    minimal = copy.deepcopy(record.get("minimal_context", {}))
    minimal["file_context"] = [
        span for span in minimal.get("file_context", []) if ends_before_target(span, record)
    ]
    minimal["lean_predecessors"] = [
        span for span in minimal.get("lean_predecessors", []) if ends_before_target(span, record)
    ]
    return minimal


def source_prefix_spans(record: dict[str, Any], window: int) -> list[dict[str, Any]]:
    spans: list[dict[str, Any]] = []
    for span in record.get("minimal_context", {}).get("source_spans", []):
        line_range = span.get("line_range") or []
        if len(line_range) != 2:
            continue
        target_start = int(line_range[0])
        prefix_end = target_start - 1
        if prefix_end < 1:
            continue
        prefix_start = max(1, prefix_end - window + 1)
        spans.append(
            {
                "path": str(span.get("path", "")),
                "line_range": [prefix_start, prefix_end],
                "method": "prefix_window_before_aligned_target_span",
                "reason": "Prefix TeX window ending strictly before aligned target source span; target span itself is withheld.",
                "source_context_derived_from_target_alignment": True,
                "labels": [],
            }
        )
    return spans


def attach_metadata(record: dict[str, Any], track: str) -> dict[str, Any]:
    row = copy.deepcopy(record)
    meta = TRACK_METADATA[track]
    row["benchmark_metadata"] = {
        "schema_version": SCHEMA_VERSION,
        "track": track,
        "leakage_level": meta["leakage_level"],
        "allowed_context_policy": meta["allowed_context_policy"],
        "target_policy": meta["target_policy"],
        "estimated_use": meta["estimated_use"],
        "limitations": meta["limitations"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    return row


def make_oracle_proof_fill(record: dict[str, Any]) -> dict[str, Any]:
    row = attach_metadata(record, "oracle_proof_fill")
    row["target_policy"] = {
        "lean_statement_available": True,
        "lean_statement_source": "target_output_chunk",
        "proof_body_expected": "replace_with_sorry_or_fill_hole",
    }
    return row


def make_oracle_source_statement(record: dict[str, Any]) -> dict[str, Any]:
    row = attach_metadata(record, "oracle_source_statement")
    row["minimal_context"] = prefix_only_context(row)
    row["target_policy"] = {
        "source_statement_available": True,
        "source_statement_may_be_target_derived": True,
        "lean_statement_available": False,
        "grading_fields_retained": ["output.lean_path", "output.declaration_names", "output.line_range"],
    }
    return row


def make_prefix_next_declaration(record: dict[str, Any], source_prefix_window: int) -> dict[str, Any]:
    row = attach_metadata(record, "prefix_next_declaration")
    minimal = prefix_only_context(row)
    minimal["source_spans"] = source_prefix_spans(row, source_prefix_window)
    row["minimal_context"] = minimal
    row["target_policy"] = {
        "source_statement_available": False,
        "source_prefix_window_lines": source_prefix_window,
        "source_prefix_window_anchored_by_target_alignment": True,
        "lean_statement_available": False,
        "grading_fields_retained": ["output.lean_path", "output.declaration_names", "output.line_range"],
    }
    return row


def split_records(records: list[dict[str, Any]], source_prefix_window: int = 120) -> dict[str, list[dict[str, Any]]]:
    return {
        "oracle_proof_fill": [make_oracle_proof_fill(record) for record in records],
        "oracle_source_statement": [make_oracle_source_statement(record) for record in records],
        "prefix_next_declaration": [
            make_prefix_next_declaration(record, source_prefix_window) for record in records
        ],
    }


def build_manifest(splits: dict[str, list[dict[str, Any]]], input_path: str | None, window: int) -> dict[str, Any]:
    generated_at = datetime.now(timezone.utc).isoformat()
    tracks: dict[str, Any] = {}
    for track, rows in splits.items():
        leakage_counts = Counter(row["benchmark_metadata"]["leakage_level"] for row in rows)
        tracks[track] = {
            "path": f"{track}.jsonl",
            "records": len(rows),
            "leakage_levels": dict(leakage_counts),
            "allowed_context_policy": TRACK_METADATA[track]["allowed_context_policy"],
            "target_policy": TRACK_METADATA[track]["target_policy"],
            "estimated_use": TRACK_METADATA[track]["estimated_use"],
            "limitations": TRACK_METADATA[track]["limitations"],
        }
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": generated_at,
        "input_path": input_path,
        "total_input_records": max((len(rows) for rows in splits.values()), default=0),
        "source_prefix_window": window,
        "tracks": tracks,
    }


def render_report(manifest: dict[str, Any]) -> str:
    lines = [
        "# Minimal Context Benchmark Splits",
        "",
        f"Generated at: `{manifest['generated_at']}`",
        f"Input: `{manifest.get('input_path') or 'in-memory records'}`",
        f"Input records: {manifest['total_input_records']}",
        f"Schema: `{manifest['schema_version']}`",
        "",
        "These splits separate oracle proof-fill examples from stricter evaluation tracks. The goal is to make leakage explicit so a 100% score says what capability was actually bought.",
        "",
    ]
    for track, info in manifest["tracks"].items():
        lines.extend(
            [
                f"## `{track}`",
                "",
                f"- File: `{info['path']}`",
                f"- Records: {info['records']}",
                f"- Leakage levels: `{info['leakage_levels']}`",
                f"- Allowed context policy: {info['allowed_context_policy']}",
                f"- Target policy: {info['target_policy']}",
                f"- Estimated use: {info['estimated_use']}",
                "- Limitations:",
            ]
        )
        for limitation in info["limitations"]:
            lines.append(f"  - {limitation}")
        lines.append("")
    lines.extend(
        [
            "## Important limitation for the prefix track",
            "",
            "The current source records are aligned to target declarations by labels/comments. The prefix track withholds the target TeX span, but its source window is still anchored by the target-derived alignment point. It is therefore marked as target-derived in each source span and should be treated as a best-effort feed-forward split, not as a fully certified chronological corpus split.",
            "",
        ]
    )
    return "\n".join(lines)


def write_splits(
    records: list[dict[str, Any]],
    output_dir: Path,
    *,
    input_path: Path | None = None,
    source_prefix_window: int = 120,
) -> dict[str, Any]:
    splits = split_records(records, source_prefix_window=source_prefix_window)
    output_dir.mkdir(parents=True, exist_ok=True)
    for track, rows in splits.items():
        write_jsonl(output_dir / f"{track}.jsonl", rows)
    manifest = build_manifest(
        splits,
        str(input_path) if input_path is not None else None,
        source_prefix_window,
    )
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (output_dir / "README.md").write_text(render_report(manifest), encoding="utf-8")
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("docs/minimal-context-gold-candidates.jsonl"))
    parser.add_argument("--output-dir", type=Path, default=Path("docs/minimal-context-splits"))
    parser.add_argument("--source-prefix-window", type=int, default=120)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.source_prefix_window < 1:
        raise SystemExit("--source-prefix-window must be positive")
    records = load_jsonl(args.input)
    manifest = write_splits(
        records,
        args.output_dir,
        input_path=args.input,
        source_prefix_window=args.source_prefix_window,
    )
    print(
        f"wrote {manifest['total_input_records']} input records into {len(manifest['tracks'])} tracks under {args.output_dir}"
    )


if __name__ == "__main__":
    main()
