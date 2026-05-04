#!/usr/bin/env python3
"""Materialize minimal-context records as bounded RepoProver smoke projects."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


NAMESPACE_RE = re.compile(r"^\s*namespace\s+(?P<name>[A-Za-z0-9_'. ]+)\s*$")
SECTION_RE = re.compile(r"^\s*section(?:\s+[A-Za-z0-9_'.]+)?\s*$")
END_RE = re.compile(r"^\s*end(?:\s+(?P<name>[A-Za-z0-9_'.]+))?\s*$")
DECL_RE = re.compile(
    r"^\s*(?:(?:private|protected|noncomputable|unsafe|partial)\s+)*"
    r"(?P<kind>theorem|lemma|def|abbrev|instance|class|structure|inductive)"
    r"(?:\s+(?P<name>[^\s:\{\(\[]+))?"
)
LEAN_WORD_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_']*")


@dataclass(frozen=True)
class SelectedRecord:
    row: dict[str, Any]

    @property
    def record_id(self) -> str:
        return str(self.row.get("id") or self.row.get("record_id"))

    @property
    def chapter_id(self) -> str:
        return str(self.row.get("chapter_id") or "minimal-context-smoke")

    @property
    def lean_path(self) -> str:
        return str(self.row["output"]["lean_path"])

    @property
    def declaration_names(self) -> list[str]:
        return [str(name) for name in self.row["output"]["declaration_names"]]

    @property
    def local_declaration_name(self) -> str:
        return self.declaration_names[0].rsplit(".", 1)[-1]

    @property
    def line_range(self) -> tuple[int, int]:
        start, end = self.row["output"]["line_range"]
        return int(start), int(end)

    @property
    def source_spans(self) -> list[dict[str, Any]]:
        return list(self.row.get("minimal_context", {}).get("source_spans", []))

    @property
    def imports(self) -> list[str]:
        return list(self.row.get("minimal_context", {}).get("imports", [])) or ["Mathlib"]

    @property
    def lean_predecessors(self) -> list[dict[str, Any]]:
        return list(self.row.get("minimal_context", {}).get("lean_predecessors", []))

    @property
    def file_context(self) -> list[dict[str, Any]]:
        return list(self.row.get("minimal_context", {}).get("file_context", []))

    @property
    def mathlib_context(self) -> list[str]:
        return list(self.row.get("minimal_context", {}).get("mathlib_context", []))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def select_records(rows: list[dict[str, Any]], record_ids: list[str], limit: int) -> list[SelectedRecord]:
    if record_ids:
        by_id = {str(row.get("id") or row.get("record_id")): row for row in rows}
        missing = [record_id for record_id in record_ids if record_id not in by_id]
        if missing:
            raise ValueError(f"record id(s) not found: {', '.join(missing)}")
        return [SelectedRecord(by_id[record_id]) for record_id in record_ids]

    def score(row: dict[str, Any]) -> tuple[float, float, float, float, int]:
        trust = row.get("trust", {})
        output = row.get("output", {})
        line_range = output.get("line_range", [0, 999999])
        span_len = int(line_range[1]) - int(line_range[0]) + 1
        return (
            float(trust.get("human_review", 0.0)),
            float(trust.get("source_span", 0.0)),
            float(trust.get("lean_dependency_graph", 0.0)),
            float(trust.get("model_extraction", 0.0)),
            -span_len,
        )

    candidates = [
        row
        for row in rows
        if len(row.get("output", {}).get("declaration_names", [])) == 1
        and row.get("output", {}).get("chunk_kind") in {"theorem", "lemma"}
    ]
    candidates.sort(key=score, reverse=True)
    return [SelectedRecord(row) for row in candidates[:limit]]


def active_namespaces_at_line(lean_file: Path, target_line: int) -> list[str]:
    stack: list[str] = []
    section_depth = 0
    for index, line in enumerate(lean_file.read_text(encoding="utf-8").splitlines(), start=1):
        if index >= target_line:
            break
        if match := NAMESPACE_RE.match(line):
            stack.append(match.group("name").strip())
        elif SECTION_RE.match(line):
            section_depth += 1
        elif END_RE.match(line):
            if section_depth > 0:
                section_depth -= 1
            elif stack:
                stack.pop()
    return stack


def read_line_range(path: Path, line_range: tuple[int, int]) -> str:
    lines = path.read_text(encoding="utf-8").splitlines()
    start, end = line_range
    return "\n".join(lines[start - 1 : end]).rstrip() + "\n"


def declaration_with_sorry(original_chunk: str) -> str:
    marker = original_chunk.find(":=")
    if marker == -1:
        raise ValueError("target declaration chunk does not contain ':='")
    return original_chunk[: marker + 2].rstrip() + " by\n  sorry\n"


def context_close_commands(file_context: list[dict[str, Any]]) -> list[str]:
    closes: list[str] = []
    for span in file_context:
        kind = str(span.get("kind") or "")
        if kind == "namespace":
            name = str(span.get("name") or "").strip()
            closes.append(f"end {name}" if name else "end")
        elif kind == "section":
            closes.append("end")
    return list(reversed(closes))


def namespace_prefix(stack: list[str]) -> str:
    return ".".join(part for part in stack if part)


def declaration_display_start(lines: list[str], declaration_index: int) -> int:
    start = declaration_index
    while start > 0:
        previous = lines[start - 1].strip()
        if previous.startswith("/--") or previous.startswith("@[") or previous.startswith("--"):
            start -= 1
            continue
        break
    return start + 1


def trim_declaration_end(lines: list[str], end_line: int) -> int:
    while end_line > 1:
        stripped = lines[end_line - 1].strip()
        if not stripped:
            end_line -= 1
            continue
        if stripped == "-/" or stripped.endswith("-/"):
            block_start = end_line
            while block_start > 1 and "/-" not in lines[block_start - 1]:
                block_start -= 1
            if block_start > 1:
                end_line = block_start - 1
                continue
        if stripped.startswith(("/--", "/-!", "--", "@[")):
            end_line -= 1
            continue
        break
    return end_line


def declarations_in_file(project_root: Path, rel_path: str) -> list[dict[str, Any]]:
    lines = (project_root / rel_path).read_text(encoding="utf-8").splitlines()
    namespace_stack: list[str] = []
    raw: list[dict[str, Any]] = []
    for index, line in enumerate(lines, start=1):
        if match := NAMESPACE_RE.match(line):
            namespace_stack.append(match.group("name").strip())
            continue
        if END_RE.match(line):
            if namespace_stack:
                namespace_stack.pop()
            continue
        match = DECL_RE.match(line)
        if not match:
            continue
        name = match.group("name")
        if not name or name.startswith(("[", "{", "(")):
            continue
        prefix = namespace_prefix(namespace_stack)
        raw.append(
            {
                "path": rel_path,
                "declaration": f"{prefix}.{name}" if prefix else name,
                "start_line": declaration_display_start(lines, index - 1),
            }
        )

    declarations: list[dict[str, Any]] = []
    for offset, row in enumerate(raw):
        next_start = raw[offset + 1]["start_line"] if offset + 1 < len(raw) else len(lines) + 1
        declarations.append(
            {
                "path": row["path"],
                "declaration": row["declaration"],
                "line_range": [row["start_line"], trim_declaration_end(lines, next_start - 1)],
                "reason": "Transitive predecessor dependency referenced by another predecessor snippet.",
                "method": "materializer_transitive_lexical_reference",
            }
        )
    return declarations


def expand_transitive_predecessors(project_root: Path, record: SelectedRecord) -> list[dict[str, Any]]:
    predecessors: list[dict[str, Any]] = []
    seen_ranges: set[tuple[str, tuple[int, int]]] = set()
    seen = set()
    seen_short_names = set()
    for row in record.lean_predecessors:
        cloned = dict(row)
        path = str(cloned["path"])
        line_range = tuple(int(value) for value in cloned["line_range"])
        declaration = str(cloned.get("declaration", ""))
        short_name = declaration.rsplit(".", 1)[-1] if declaration else ""
        range_key = (path, line_range)
        decl_key = (path, declaration) if declaration else None
        short_key = (path, short_name) if short_name else None
        if (
            range_key in seen_ranges
            or (decl_key is not None and decl_key in seen)
            or (short_key is not None and short_key in seen_short_names)
        ):
            continue
        predecessors.append(cloned)
        seen_ranges.add(range_key)
        if decl_key is not None:
            seen.add(decl_key)
        if short_key is not None:
            seen_short_names.add(short_key)
    paths = {str(row["path"]) for row in predecessors}
    declarations_by_path = {path: declarations_in_file(project_root, path) for path in paths}

    changed = True
    while changed:
        changed = False
        for predecessor in list(predecessors):
            path = str(predecessor["path"])
            start, end = [int(value) for value in predecessor["line_range"]]
            words = set(LEAN_WORD_RE.findall(read_line_range(project_root / path, (start, end))))
            for candidate in declarations_by_path.get(path, []):
                candidate_start = int(candidate["line_range"][0])
                key = (path, str(candidate["declaration"]))
                range_key = (path, tuple(int(value) for value in candidate["line_range"]))
                short_name = str(candidate["declaration"]).rsplit(".", 1)[-1]
                short_key = (path, short_name)
                if key in seen or short_key in seen_short_names or range_key in seen_ranges or candidate_start >= start:
                    continue
                if short_name not in words:
                    continue
                predecessors.append(dict(candidate))
                seen.add(key)
                seen_short_names.add(short_key)
                seen_ranges.add(range_key)
                changed = True

    return sorted(predecessors, key=lambda row: (str(row["path"]), int(row["line_range"][0])))


def module_name_from_lean_path(path: str) -> str:
    return path.removesuffix(".lean").replace("/", ".")


def write_source_snippets(project_root: Path, output_root: Path, record: SelectedRecord) -> str:
    if not record.source_spans:
        source_path = "tex/minimal-context-smoke.tex"
        destination = output_root / source_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text("% No source span was recorded for this example.\n", encoding="utf-8")
        return source_path

    first_source_path = str(record.source_spans[0]["path"])
    for span in record.source_spans:
        rel = str(span["path"])
        source_file = project_root / rel
        destination = output_root / rel
        destination.parent.mkdir(parents=True, exist_ok=True)
        start, end = [int(value) for value in span["line_range"]]
        labels = ", ".join(span.get("labels", [])) or "unlabeled"
        snippet = read_line_range(source_file, (start, end))
        header = f"% Minimal-context source span from {rel}:{start}-{end} ({labels})\n"
        mode = "a" if destination.exists() else "w"
        with destination.open(mode, encoding="utf-8") as handle:
            if mode == "a":
                handle.write("\n")
            handle.write(header)
            handle.write(snippet)
    return first_source_path


def render_file_context(project_root: Path, record: SelectedRecord) -> tuple[list[str], list[str]]:
    if record.file_context:
        parts: list[str] = []
        for span in record.file_context:
            path = project_root / str(span["path"])
            start, end = [int(value) for value in span["line_range"]]
            parts.append(f"-- File context: {span['path']}:{start}-{end} ({span.get('kind', 'context')})")
            parts.append(read_line_range(path, (start, end)).rstrip())
        return parts, context_close_commands(record.file_context)

    lean_file = project_root / record.lean_path
    namespaces = active_namespaces_at_line(lean_file, record.line_range[0])
    parts = [f"namespace {namespace}" for namespace in namespaces]
    closes = [f"end {namespace}" for namespace in reversed(namespaces)]
    return parts, closes


def render_ordered_context_and_predecessors(project_root: Path, record: SelectedRecord) -> tuple[list[str], list[str]]:
    context_closes = context_close_commands(record.file_context)
    items: list[tuple[tuple[int, int, int], list[str]]] = []
    ordinal = 0

    if record.file_context:
        for span in record.file_context:
            path = str(span["path"])
            start, end = [int(value) for value in span["line_range"]]
            items.append(
                (
                    (0 if path == record.lean_path else 1, start, ordinal),
                    [
                        f"-- File context: {span['path']}:{start}-{end} ({span.get('kind', 'context')})",
                        read_line_range(project_root / path, (start, end)).rstrip(),
                    ],
                )
            )
            ordinal += 1
    else:
        context_parts, context_closes = render_file_context(project_root, record)
        for part in context_parts:
            items.append(((0, 0, ordinal), [part]))
            ordinal += 1

    for predecessor in expand_transitive_predecessors(project_root, record):
        path = str(predecessor["path"])
        start, end = [int(value) for value in predecessor["line_range"]]
        items.append(
            (
                (0 if path == record.lean_path else 1, start, ordinal),
                [
                    f"-- Predecessor context: {predecessor['path']}:{start}-{end}",
                    read_line_range(project_root / path, (start, end)).rstrip(),
                ],
            )
        )
        ordinal += 1

    parts: list[str] = []
    for _, rendered in sorted(items, key=lambda item: item[0]):
        parts.extend(rendered)
        parts.append("")
    if parts and parts[-1] == "":
        parts.pop()
    return parts, context_closes


def build_target_lean(project_root: Path, record: SelectedRecord, *, use_record_imports: bool = False) -> str:
    lean_file = project_root / record.lean_path
    target_chunk = declaration_with_sorry(read_line_range(lean_file, record.line_range))
    context_parts, context_closes = render_ordered_context_and_predecessors(project_root, record)
    imports = record.imports if use_record_imports else ["Mathlib"]

    parts: list[str] = []
    for module in imports:
        parts.append(f"import {module}")
    parts.append("")
    parts.append("/-!")
    parts.append(f"Minimal-context smoke target generated from `{record.record_id}`.")
    if record.mathlib_context:
        parts.append("")
        parts.append("Mathlib/API context recorded for the example:")
        for item in record.mathlib_context:
            parts.append(f"- {item}")
    parts.append("-/")
    parts.append("")

    parts.extend(context_parts)
    if context_parts:
        parts.append("")

    parts.append(target_chunk.rstrip())
    parts.append("")
    parts.extend(context_closes)
    return "\n".join(parts).rstrip() + "\n"


def ensure_mathlib_cache_decompressed(cache_from: Path) -> None:
    """Ensure a source Lake cache has importable Mathlib oleans.

    `--lake-cache-from` symlinks an existing `.lake/packages` directory into the
    materialized smoke project.  That avoids recloning dependencies, but Lean can
    still fail with `unknown module prefix 'Mathlib'` when the mathlib package is
    present only as source and its downloaded cache has not been decompressed.
    """
    mathlib_olean = cache_from / ".lake" / "packages" / "mathlib" / ".lake" / "build" / "lib" / "lean" / "Mathlib.olean"
    if mathlib_olean.exists():
        return
    if not (cache_from / "lakefile.lean").exists() and not (cache_from / "lakefile.toml").exists():
        return
    env = os.environ.copy()
    env.setdefault("MATHLIB_CACHE_USE_CLOUDFLARE", "1")
    subprocess.run(
        ["uv", "run", "lake", "exe", "cache", "get", "Mathlib"],
        cwd=cache_from,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=600,
        check=True,
        env=env,
    )


def copy_lake_cache(cache_from: Path, output_root: Path) -> None:
    cache_from = cache_from.resolve()
    source_lake = cache_from / ".lake"
    if not source_lake.exists():
        raise ValueError(f"lake cache source does not exist: {source_lake}")
    ensure_mathlib_cache_decompressed(cache_from)
    lake_dir = output_root / ".lake"
    lake_dir.mkdir(exist_ok=True)
    for name in ("packages",):
        target = lake_dir / name
        if not target.exists():
            target.symlink_to(source_lake / name, target_is_directory=True)


def copy_project_config(project_root: Path, output_root: Path) -> None:
    for filename in ("lean-toolchain", "lake-manifest.json"):
        source = project_root / filename
        if source.exists():
            shutil.copy2(source, output_root / filename)

    lakefile = project_root / "lakefile.lean"
    if not lakefile.exists():
        return
    lines = lakefile.read_text(encoding="utf-8").splitlines()
    filtered: list[str] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if line.strip() == "require checkdecls from git":
            index += 1
            while index < len(lines) and (not lines[index].strip() or lines[index].startswith((" ", "\t"))):
                index += 1
            continue
        filtered.append(line)
        index += 1
    (output_root / "lakefile.lean").write_text("\n".join(filtered).rstrip() + "\n", encoding="utf-8")


def write_repoprover_state(output_root: Path, record: SelectedRecord, source_path: str) -> None:
    state = {
        "book_id": output_root.name,
        "chapters": {
            record.chapter_id: {
                "title": f"Minimal context smoke for {record.local_declaration_name}",
                "source_path": source_path,
                "lean_path": record.lean_path,
                "target_theorems": [record.local_declaration_name],
                "sketch_merged": True,
            }
        },
        "prs": {},
        "completed_theorems": {},
        "next_issue_id": 1,
        "max_concurrent_scanners": 1,
        "active_scanners": {},
        "max_concurrent_progress": 1,
        "active_progress": {},
    }
    state_path = output_root / ".repoprover" / "state.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def materialize_smoke_project(
    project_root: Path,
    output_root: Path,
    records: list[SelectedRecord],
    *,
    force: bool = False,
    lake_cache_from: Path | None = None,
    init_git: bool = True,
    use_record_imports: bool = False,
) -> None:
    if not records:
        raise ValueError("no records selected")
    if len(records) != 1:
        raise ValueError("only one selected record per smoke project is currently supported")
    record = records[0]

    if output_root.exists():
        if not force:
            raise FileExistsError(f"output already exists: {output_root}")
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True)

    copy_project_config(project_root, output_root)

    source_path = write_source_snippets(project_root, output_root, record)

    target_lean = output_root / record.lean_path
    target_lean.parent.mkdir(parents=True, exist_ok=True)
    target_lean.write_text(build_target_lean(project_root, record, use_record_imports=use_record_imports), encoding="utf-8")

    root_module = Path(record.lean_path).parts[0]
    root_import = output_root / f"{root_module}.lean"
    root_import.write_text(f"import {module_name_from_lean_path(record.lean_path)}\n", encoding="utf-8")

    manifest = {
        "chapters": [
            {
                "id": record.chapter_id,
                "title": f"Minimal context smoke for {record.local_declaration_name}",
                "source_path": source_path,
                "lean_path": record.lean_path,
                "target_theorems": [record.local_declaration_name],
            }
        ]
    }
    (output_root / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    contents = [
        "# Minimal Context Smoke",
        "",
        f"- Record: `{record.record_id}`",
        f"- Target: `{record.local_declaration_name}`",
        f"- Lean file: `{record.lean_path}`",
        f"- Source file: `{source_path}`",
        "",
        "The chapter is pre-marked as sketched in `.repoprover/state.json` so",
        "RepoProver launches a prover for the target `sorry` instead of a sketcher.",
        "",
    ]
    (output_root / "CONTENTS.md").write_text("\n".join(contents), encoding="utf-8")

    write_repoprover_state(output_root, record, source_path)
    (output_root / ".gitignore").write_text(".repoprover/\nruns/\n.lake/\n", encoding="utf-8")
    if lake_cache_from:
        copy_lake_cache(lake_cache_from, output_root)

    if init_git:
        subprocess.run(["git", "init", "-b", "main"], cwd=output_root, check=True, capture_output=True, text=True)
        subprocess.run(["git", "add", "-A"], cwd=output_root, check=True, capture_output=True, text=True)
        subprocess.run(
            ["git", "commit", "-m", f"Materialize minimal-context smoke for {record.local_declaration_name}"],
            cwd=output_root,
            check=True,
            capture_output=True,
            text=True,
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", type=Path, default=Path("docs/minimal-context-gold-candidates.jsonl"))
    parser.add_argument("--project-root", type=Path, default=Path("algebraic-combinatorics"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--record-id", action="append", default=[], help="Record id to materialize.")
    parser.add_argument("--limit", type=int, default=1, help="Number of auto-selected records. Currently must be 1.")
    parser.add_argument("--force", action="store_true", help="Overwrite the output directory.")
    parser.add_argument("--no-git", action="store_true", help="Do not initialize a git repository in the output.")
    parser.add_argument(
        "--lake-cache-from",
        type=Path,
        help="Optional Lean project whose .lake/packages directory should be symlinked for a cheap dry build.",
    )
    parser.add_argument(
        "--include-record-imports",
        action="store_true",
        help="Import the record's local import list instead of the default Mathlib-only benchmark baseline.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    rows = load_jsonl(args.records)
    selected = select_records(rows, args.record_id, args.limit)
    materialize_smoke_project(
        args.project_root,
        args.output,
        selected,
        force=args.force,
        lake_cache_from=args.lake_cache_from,
        init_git=not args.no_git,
        use_record_imports=args.include_record_imports,
    )
    record = selected[0]
    print(f"Materialized {record.record_id}")
    print(f"Project: {args.output}")
    print(
        "Run: uv run python -m repoprover run "
        f"{args.output} --pool-size 1 --provider openrouter --model deepseek/deepseek-v4-pro "
        "--no-background-agents --stop-after-first-merge --verbose"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
