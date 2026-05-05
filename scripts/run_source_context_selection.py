#!/usr/bin/env python3
"""Run source-only context selection before source-to-Lean generation.

The selector prompt sees source-only statement context and prefix/local Lean
context, but not the target Lean declaration name, statement, or proof. Its job
is to sketch the formalization and request a tight set of local and Mathlib API
facts that should be placed into the later generation context pack.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import re
import subprocess
import sys
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.materialize_minimal_context_smoke import SelectedRecord, load_jsonl, read_line_range  # noqa: E402
from scripts.review_minimal_context_records import DEFAULT_BASE_URL  # noqa: E402
from scripts.run_minimal_context_eval import (  # noqa: E402
    DEFAULT_MODEL,
    DEFAULT_PRICE,
    OpenRouterPrice,
    estimate_payload_cost,
    summarize_openrouter_response_cost,
    write_json,
    write_jsonl,
)
from scripts.run_source_statement_live_eval import (  # noqa: E402
    build_payload,
    build_prompt_context,
    call_openrouter,
    parse_model_json,
    response_finish_reason,
    response_message_content,
    select_source_statement_records,
    write_text_artifact,
)

PLACEHOLDER_MATHLIB_CONTEXT_RE = re.compile(
    r"exact proof-level facts not statically certified|^mathlib context$",
    re.IGNORECASE,
)
DECL_RE = re.compile(
    r"^\s*(?:(?:private|protected|noncomputable|unsafe|partial)\s+)*"
    r"(?:theorem|lemma|def|abbrev|instance|class|structure|inductive)\s+"
    r"(?P<name>[^\s:\{\(\[]+)"
)
QUALIFIED_IDENTIFIER_RE = re.compile(r"\b[A-Za-z_][A-Za-z0-9_']*(?:\.[A-Za-z_][A-Za-z0-9_']*)+\b")
BARE_IDENTIFIER_RE = re.compile(r"\b[A-Za-z_][A-Za-z0-9_']*\b")
LEAN_KEYWORDS = {
    "by",
    "theorem",
    "lemma",
    "def",
    "abbrev",
    "instance",
    "class",
    "structure",
    "inductive",
    "namespace",
    "section",
    "variable",
    "where",
    "if",
    "then",
    "else",
    "fun",
    "forall",
    "exists",
    "have",
    "show",
    "let",
    "in",
    "match",
    "with",
    "simp",
    "rw",
    "rfl",
    "exact",
    "apply",
    "intro",
    "intros",
    "constructor",
    "refine",
    "calc",
}


def openrouter_price_for_model(model: str) -> OpenRouterPrice:
    request = urllib.request.Request("https://openrouter.ai/api/v1/models", headers={"User-Agent": "repoprover-context-selector"})
    with urllib.request.urlopen(request, timeout=30) as response:
        catalog = json.loads(response.read().decode("utf-8"))
    for item in catalog.get("data") or []:
        if item.get("id") != model:
            continue
        pricing = item.get("pricing") or {}
        return OpenRouterPrice(
            model=model,
            prompt_per_token=float(pricing.get("prompt") or DEFAULT_PRICE.prompt_per_token),
            completion_per_token=float(pricing.get("completion") or DEFAULT_PRICE.completion_per_token),
            context_length=item.get("context_length"),
            source="openrouter-catalog-live",
        )
    return OpenRouterPrice(
        model=model,
        prompt_per_token=DEFAULT_PRICE.prompt_per_token,
        completion_per_token=DEFAULT_PRICE.completion_per_token,
        context_length=DEFAULT_PRICE.context_length,
        source=f"{DEFAULT_PRICE.source}-fallback-model-not-found",
    )


@dataclass(frozen=True)
class BatchItem:
    public_key: str
    record: SelectedRecord


def useful_existing_mathlib_context(items: list[str]) -> list[str]:
    useful: list[str] = []
    for item in items:
        text = str(item).strip()
        if not text or PLACEHOLDER_MATHLIB_CONTEXT_RE.search(text):
            continue
        useful.append(text)
    return useful


def mathlib_overview(project_root: Path, *, max_entries: int = 80) -> dict[str, Any]:
    mathlib_root = project_root / ".lake" / "packages" / "mathlib" / "Mathlib"
    if not mathlib_root.exists():
        return {
            "mathlib_source_available": False,
            "policy": "Return search queries and expected API names; hydration will resolve them if Mathlib source is available.",
        }
    top_level = sorted(path.name for path in mathlib_root.iterdir() if path.is_dir())
    second_level: list[str] = []
    for path in sorted(mathlib_root.iterdir()):
        if not path.is_dir():
            continue
        for child in sorted(path.iterdir()):
            if child.is_dir():
                second_level.append(f"{path.name}/{child.name}")
    return {
        "mathlib_source_available": True,
        "top_level_directories": top_level[:max_entries],
        "selected_second_level_directories": second_level[:max_entries],
        "policy": (
            "Use this only as a map. Return exact declaration names when known, "
            "and return narrow search queries when unsure."
        ),
    }


def selector_record_payload(project_root: Path, item: BatchItem) -> dict[str, Any]:
    context = build_prompt_context(project_root, item.record, context_mode="source-only")
    legacy_mathlib = useful_existing_mathlib_context(list(context.pop("mathlib_context", []) or []))
    payload = {
        "record_key": item.public_key,
        "source_statement_or_chunk": context.get("source_statement_or_chunk"),
        "tex_source_focus": context.get("tex_source_focus"),
        "target_source_focus": context.get("target_source_focus"),
        "source_progress_context": context.get("source_progress_context"),
        "available_imports": context.get("available_imports"),
        "lean_prefix_context": context.get("lean_prefix_context"),
        "lean_environment": context.get("lean_environment"),
        "local_lean_style": context.get("local_lean_style"),
        "domain_statement_shape_guidance": context.get("domain_statement_shape_guidance"),
        "benchmark_policy": context.get("benchmark_policy"),
    }
    if legacy_mathlib:
        payload["legacy_mathlib_context"] = legacy_mathlib
    return payload


def build_context_selection_messages(
    project_root: Path,
    items: list[BatchItem],
    *,
    max_context_tokens: int,
    round_name: str,
) -> list[dict[str, str]]:
    system = (
        "You are a Lean 4/Mathlib context-selection agent. Your task is to prepare "
        "a compact context pack for a later autoformalization agent. You see only "
        "source-side mathematical text plus prefix/local Lean context. The target "
        "Lean declaration name, statement, and proof are withheld. Return exactly "
        "one JSON object."
    )
    schema = {
        "records": [
            {
                "record_key": "record-001",
                "source_focus_summary": "what precise source statement or part should be formalized",
                "selected_source_part": "specific source part/label chosen for formalization, or whole statement if unambiguous",
                "source_part_rationale": "why this part was chosen, using source labels and prefix progress when available",
                "formalization_sketch": [
                    "Lean-level sketch of the likely statement shape and proof plan, without inventing hidden target names"
                ],
                "needed_local_context": [
                    {
                        "name_or_snippet": "displayed local declaration/notation/variable needed",
                        "why_needed": "role in statement/proof",
                    }
                ],
                "mathlib_queries": [
                    "narrow Mathlib search phrase or expected declaration name, e.g. Nat.choose_symm"
                ],
                "candidate_mathlib_context": [
                    {
                        "name": "exact or likely Mathlib declaration name",
                        "kind": "theorem|lemma|def|notation|tactic|typeclass|unknown",
                        "expected_signature_or_shape": "signature shape if known",
                        "why_needed": "why this belongs in the later context pack",
                        "confidence": 0.0,
                    }
                ],
                "proof_notes": ["brief notes that may prevent API/type-signature mistakes"],
                "uncertainties": ["what may require Mathlib/source lookup in a second round"],
            }
        ]
    }
    user = {
        "task": (
            "For each record, sketch the formalization and select the tight local/Mathlib "
            "context a later proof-writing model should see. Prefer a few thousand tokens "
            "or less of Mathlib facts per record."
        ),
        "round": round_name,
        "required_json_schema": schema,
        "selection_budget": {
            "max_added_context_tokens_per_record": max_context_tokens,
            "prefer_exact_signatures_over_long_files": True,
            "prefer_few_precise_facts_over_broad_import_dumps": True,
        },
        "instructions": [
            "Do not ask for or infer the withheld target Lean declaration name, statement, or proof.",
            "Do not rely on legacy broad `Mathlib` imports as context; select concrete APIs/signatures/docstrings needed by the later generator.",
            "If a Mathlib name is uncertain, return a narrow search query plus the expected type/signature shape.",
            "Include previous formalized local declarations only if they are displayed in the prefix/local context.",
            "If `source_progress_context.prior_same_label_declarations` shows that an earlier declaration already formalized a lettered source part, do not re-formalize that part or bundle it into a conjunction; select the remaining/next part.",
            "Separate mathematical understanding from Lean API uncertainty in `uncertainties`.",
            "Do not over-select: every requested fact should have a role in statement typing or proof construction.",
        ],
        "global_mathlib_overview": mathlib_overview(project_root),
        "records": [selector_record_payload(project_root, item) for item in items],
    }
    return [{"role": "system", "content": system}, {"role": "user", "content": json.dumps(user, indent=2, ensure_ascii=False)}]


def extract_candidate_names(selection: dict[str, Any]) -> list[str]:
    names: list[str] = []
    for item in selection.get("candidate_mathlib_context") or []:
        if isinstance(item, dict):
            value = str(item.get("name") or "").strip()
        else:
            value = str(item).strip()
        if value and value.lower() not in {"unknown", "n/a", "none"} and value not in names:
            names.append(value.strip("`"))
    return names


def extract_queries(selection: dict[str, Any]) -> list[str]:
    queries: list[str] = []
    for item in selection.get("mathlib_queries") or []:
        value = str(item).strip().strip("`")
        if value and value not in queries:
            queries.append(value)
    for name in extract_candidate_names(selection):
        if name not in queries:
            queries.append(name)
    return queries


def mathlib_root_from_workspace(workspace: Path) -> Path | None:
    candidates = [
        workspace / ".lake" / "packages" / "mathlib",
        workspace,
    ]
    for candidate in candidates:
        if (candidate / "Mathlib").exists():
            return candidate
    return None


def read_declaration_snippet(file_path: Path, line_number: int, *, max_lines: int = 28) -> str:
    lines = file_path.read_text(encoding="utf-8").splitlines()
    start = max(0, line_number - 1)
    if start > 0 and lines[start - 1].strip().endswith("-/"):
        comment_start = start - 1
        while comment_start > 0 and not lines[comment_start].lstrip().startswith(("/--", "/-!")):
            comment_start -= 1
        if lines[comment_start].lstrip().startswith(("/--", "/-!")):
            start = comment_start
    end = min(len(lines), line_number - 1 + max_lines)
    for index in range(line_number, end):
        if index > line_number and DECL_RE.match(lines[index]):
            end = index
            break
    return "\n".join(lines[start:end]).rstrip()


def rg_mathlib(mathlib_root: Path, pattern: str, *, max_results: int = 5, literal: bool = False) -> list[dict[str, Any]]:
    cmd = ["rg", "--json", "-g", "*.lean"]
    if literal:
        cmd.append("-F")
    cmd.extend(["--", pattern, str(mathlib_root / "Mathlib")])
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, check=False)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []
    matches: list[dict[str, Any]] = []
    for line in result.stdout.splitlines():
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if payload.get("type") != "match":
            continue
        data = payload.get("data") or {}
        path = Path(data.get("path", {}).get("text", ""))
        line_number = int(data.get("line_number") or 0)
        if not path.exists() or line_number <= 0:
            continue
        try:
            rel_path = str(path.relative_to(mathlib_root))
        except ValueError:
            rel_path = str(path)
        matches.append(
            {
                "file": rel_path,
                "line": line_number,
                "text": str(data.get("lines", {}).get("text", "")).rstrip(),
                "snippet": read_declaration_snippet(path, line_number),
            }
        )
        if len(matches) >= max_results:
            break
    return matches


def find_mathlib_declaration(mathlib_root: Path, name: str, *, max_results: int = 3) -> list[dict[str, Any]]:
    short_name = name.split(".")[-1].strip()
    if not short_name:
        return []
    pattern = (
        r"^\s*(?:(?:private|protected|noncomputable|unsafe|partial)\s+)*"
        r"(?:theorem|lemma|def|abbrev|instance|class|structure|inductive)\s+"
        + re.escape(short_name)
        + r"\b"
    )
    return rg_mathlib(mathlib_root, pattern, max_results=max_results)


def hydrate_mathlib_context(
    model_json: dict[str, Any],
    *,
    mathlib_workspace: Path,
    max_results_per_query: int,
) -> dict[str, Any]:
    mathlib_root = mathlib_root_from_workspace(mathlib_workspace)
    if mathlib_root is None:
        return {"mathlib_source_available": False, "records": []}
    hydrated_records: list[dict[str, Any]] = []
    for selection in model_json.get("records") or []:
        record_key = str(selection.get("record_key") or "")
        resolved: list[dict[str, Any]] = []
        seen_queries: set[str] = set()
        for query in extract_queries(selection):
            if query in seen_queries:
                continue
            seen_queries.add(query)
            matches = find_mathlib_declaration(mathlib_root, query, max_results=max_results_per_query)
            if not matches:
                matches = rg_mathlib(mathlib_root, query, max_results=max_results_per_query, literal=True)
            resolved.append({"query": query, "matches": matches})
        hydrated_records.append({"record_key": record_key, "resolved_mathlib_context": resolved})
    return {
        "mathlib_source_available": True,
        "mathlib_root": str(mathlib_root),
        "records": hydrated_records,
    }


def lean_identifiers(text: str) -> list[str]:
    identifiers: list[str] = []
    for match in QUALIFIED_IDENTIFIER_RE.findall(text):
        if match not in identifiers:
            identifiers.append(match)
    for token in BARE_IDENTIFIER_RE.findall(text):
        if token in LEAN_KEYWORDS or len(token) <= 2:
            continue
        if token[0].islower() and token not in {"omega", "ring", "linarith", "norm_num"}:
            continue
        if token not in identifiers:
            identifiers.append(token)
    return identifiers


def compare_selection_to_gold(
    project_root: Path,
    items: list[BatchItem],
    model_json: dict[str, Any],
) -> dict[str, Any]:
    by_key = {item.public_key: item.record for item in items}
    rows: list[dict[str, Any]] = []
    for selection in model_json.get("records") or []:
        key = str(selection.get("record_key") or "")
        record = by_key.get(key)
        if record is None:
            continue
        gold_text = read_line_range(project_root / record.lean_path, record.line_range)
        selected_names = extract_candidate_names(selection)
        selected_short_names = {name.split(".")[-1] for name in selected_names}
        gold_ids = lean_identifiers(gold_text)
        gold_short_ids = {name.split(".")[-1] for name in gold_ids}
        rows.append(
            {
                "record_key": key,
                "record_id": record.record_id,
                "selected_mathlib_names": selected_names,
                "gold_identifier_sample": gold_ids[:80],
                "selected_name_gold_overlap": sorted(selected_short_names & gold_short_ids),
                "selected_name_count": len(selected_names),
                "gold_identifier_count": len(gold_ids),
                "policy": "Gold text is used only after model selection output is written; it is never included in selector prompts.",
            }
        )
    return {"records": rows}


def batched(items: list[BatchItem], batch_size: int) -> list[list[BatchItem]]:
    return [items[index : index + batch_size] for index in range(0, len(items), batch_size)]


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def run_batch(args: argparse.Namespace, batch_index: int, items: list[BatchItem]) -> dict[str, Any]:
    batch_dir = args.output / f"batch-{batch_index:03d}"
    batch_dir.mkdir(parents=True, exist_ok=True)
    messages = build_context_selection_messages(
        args.project_root,
        items,
        max_context_tokens=args.max_context_tokens_per_record,
        round_name=args.round_name,
    )
    payload = build_payload(
        model=args.model,
        messages=messages,
        max_tokens=args.max_tokens,
        temperature=args.temperature,
        reasoning_effort=args.reasoning_effort,
    )
    write_json(batch_dir / "context-selection-payload.json", payload)
    write_jsonl(batch_dir / "records-manifest.jsonl", [{"record_key": item.public_key, "record": item.record.row} for item in items])
    estimate = estimate_payload_cost(payload, args.price)
    row: dict[str, Any] = {
        "batch_index": batch_index,
        "record_keys": [item.public_key for item in items],
        "record_ids": [item.record.record_id for item in items],
        "budget_estimate": estimate,
        "paid_call_made": False,
    }
    if args.budget_only:
        row["status"] = "budget_only"
        return row

    response_path = batch_dir / "context-selection-response.json"
    if getattr(args, "reuse_existing_responses", False) and response_path.exists():
        response = json.loads(response_path.read_text(encoding="utf-8"))
        row["reused_existing_response"] = True
    else:
        response = call_openrouter(payload, args.base_url, args.openrouter_timeout)
    row["paid_call_made"] = True
    row["response_received"] = True
    row["finish_reason"] = response_finish_reason(response)
    write_json(response_path, response)
    cost_summary = summarize_openrouter_response_cost(response, args.price)
    write_json(batch_dir / "context-selection-cost-summary.json", cost_summary)
    row["cost_summary"] = cost_summary
    assistant_content = response_message_content(response)
    write_text_artifact(batch_dir / "context-selection-assistant-content.txt", assistant_content)
    try:
        if not assistant_content.strip():
            raise ValueError("model returned empty content")
        model_json = parse_model_json(response)
    except Exception as exc:  # noqa: BLE001 - malformed selector output is a row-level result.
        row["success"] = False
        row["failure_class"] = "no_content_or_length" if row["finish_reason"] == "length" else "invalid_model_json"
        row["error"] = f"{type(exc).__name__}: {exc}"
        return row
    write_json(batch_dir / "context-selection-output.json", model_json)
    row["model_output_record_count"] = len(model_json.get("records") or [])
    if args.hydrate_mathlib:
        hydrated = hydrate_mathlib_context(
            model_json,
            mathlib_workspace=args.mathlib_workspace or args.project_root,
            max_results_per_query=args.max_mathlib_results_per_query,
        )
        write_json(batch_dir / "mathlib-hydrated-context.json", hydrated)
        row["hydrated_mathlib_records"] = len(hydrated.get("records") or [])
    if args.compare_gold:
        comparison = compare_selection_to_gold(args.project_root, items, model_json)
        write_json(batch_dir / "gold-comparison.json", comparison)
        row["gold_comparison_records"] = len(comparison.get("records") or [])
    row["success"] = True
    return row


def actual_cost_from_batch(row: dict[str, Any]) -> float:
    cost_summary = row.get("cost_summary") or {}
    if cost_summary.get("actual_cost_usd") is None:
        return 0.0
    return float(cost_summary["actual_cost_usd"])


def audit_payload_target_name_leaks(output: Path, items: list[BatchItem]) -> dict[str, Any]:
    leaks: list[dict[str, str]] = []
    for payload_path in sorted(output.glob("batch-*/context-selection-payload.json")):
        text = payload_path.read_text(encoding="utf-8")
        for item in items:
            for name in item.record.declaration_names:
                short_name = name.split(".")[-1]
                if name in text or short_name in text:
                    leaks.append(
                        {
                            "payload": str(payload_path),
                            "record_key": item.public_key,
                            "record_id": item.record.record_id,
                            "declaration_name": name,
                        }
                    )
    return {"leak_count": len(leaks), "leaks": leaks}


def run(args: argparse.Namespace) -> dict[str, Any]:
    if not hasattr(args, "price"):
        if getattr(args, "use_live_catalog_prices", True):
            args.price = openrouter_price_for_model(args.model)
        else:
            args.price = DEFAULT_PRICE
    rows = load_jsonl(args.records)
    selected = select_source_statement_records(rows, args.limit, args.sample_mode)
    items = [BatchItem(public_key=f"record-{item.index:03d}", record=item.selected) for item in selected]
    if not items:
        raise ValueError("no source-statement theorem/lemma records selected")
    if args.batch_size < 1:
        raise ValueError("--batch-size must be at least 1")
    if args.concurrency < 1:
        raise ValueError("--concurrency must be at least 1")
    args.output.mkdir(parents=True, exist_ok=True)
    eval_dir = args.output / "eval"
    eval_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(eval_dir / "selected-records.jsonl", [item.record.row for item in items])

    batches = batched(items, args.batch_size)
    partial_jsonl = eval_dir / "partial-results.jsonl"
    if partial_jsonl.exists():
        partial_jsonl.unlink()
    results_by_batch: dict[int, dict[str, Any]] = {}
    total_cost = 0.0

    if args.budget_only or args.concurrency == 1:
        for batch_index, batch_items in enumerate(batches, start=1):
            row = run_batch(args, batch_index, batch_items)
            total_cost += actual_cost_from_batch(row)
            if args.max_actual_cost_usd and total_cost > args.max_actual_cost_usd:
                row["failure_class"] = "cost_cap_exceeded_after_call"
            results_by_batch[batch_index] = row
            append_jsonl(partial_jsonl, row)
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as executor:
            future_to_index = {
                executor.submit(run_batch, args, batch_index, batch_items): batch_index
                for batch_index, batch_items in enumerate(batches, start=1)
            }
            for future in concurrent.futures.as_completed(future_to_index):
                batch_index = future_to_index[future]
                try:
                    row = future.result()
                except Exception as exc:  # noqa: BLE001
                    row = {
                        "batch_index": batch_index,
                        "paid_call_made": False,
                        "success": False,
                        "failure_class": "worker_error",
                        "error": f"{type(exc).__name__}: {exc}",
                    }
                total_cost += actual_cost_from_batch(row)
                results_by_batch[batch_index] = row
                append_jsonl(partial_jsonl, row)

    results = [results_by_batch[index] for index in sorted(results_by_batch)]
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "records_selected": len(items),
        "batches": len(batches),
        "batch_size": args.batch_size,
        "model": args.model,
        "price_source": args.price.source,
        "prompt_price_per_million": args.price.prompt_per_token * 1_000_000,
        "completion_price_per_million": args.price.completion_per_token * 1_000_000,
        "context_length": args.price.context_length,
        "max_tokens": args.max_tokens,
        "reasoning_effort": args.reasoning_effort,
        "round_name": args.round_name,
        "budget_only": args.budget_only,
        "paid_calls_made": sum(1 for row in results if row.get("paid_call_made")),
        "actual_cost_usd": total_cost,
        "max_actual_cost_usd": args.max_actual_cost_usd,
        "hydrate_mathlib": args.hydrate_mathlib,
        "compare_gold": args.compare_gold,
        "sample_mode": args.sample_mode,
        "payload_target_name_audit": audit_payload_target_name_leaks(args.output, items),
        "results": results,
    }
    write_json(eval_dir / "context-selection-results.json", summary)
    render_markdown(eval_dir / "context-selection-results.md", summary)
    return summary


def render_markdown(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# Source context-selection results",
        "",
        f"- Generated at: `{summary['generated_at']}`",
        f"- Model: `{summary['model']}`",
        f"- Price source: `{summary['price_source']}`",
        f"- Prompt/completion price per 1M tokens: `${summary['prompt_price_per_million']:.6f}` / `${summary['completion_price_per_million']:.6f}`",
        f"- Context length: `{summary['context_length']}`",
        f"- Max tokens: `{summary['max_tokens']}`",
        f"- Reasoning effort: `{summary['reasoning_effort']}`",
        f"- Round: `{summary['round_name']}`",
        f"- Budget only: `{summary['budget_only']}`",
        f"- Records selected: `{summary['records_selected']}`",
        f"- Batches: `{summary['batches']}` of size `{summary['batch_size']}`",
        f"- Paid calls made: `{summary['paid_calls_made']}`",
        f"- Actual reported cost: `${summary['actual_cost_usd']:.6f}`",
        f"- Hydrate Mathlib: `{summary['hydrate_mathlib']}`",
        f"- Compare gold after selection: `{summary['compare_gold']}`",
        f"- Payload target-name leaks: `{summary['payload_target_name_audit']['leak_count']}`",
        "",
        "Selector prompts use source-only context and do not include target Lean declaration names, statements, or proofs. Gold comparison, when enabled, is written only after selector output exists.",
        "",
        "| Batch | Records | Paid | Cost | Status |",
        "|---:|---:|---|---:|---|",
    ]
    for row in summary["results"]:
        cost = actual_cost_from_batch(row)
        status = row.get("failure_class") or row.get("status") or ("ok" if row.get("success") else "")
        lines.append(
            f"| {row['batch_index']} | {len(row.get('record_keys') or [])} | {row.get('paid_call_made')} | ${cost:.6f} | `{status}` |"
        )
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", type=Path, default=REPO_ROOT / "docs/minimal-context-gold-candidates.jsonl")
    parser.add_argument("--project-root", type=Path, default=REPO_ROOT / "algebraic-combinatorics")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=8)
    parser.add_argument("--sample-mode", choices=["corpus-spread", "easy", "stratified-easy"], default="corpus-spread")
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--concurrency", type=int, default=1)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--max-tokens", type=int, default=8192)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--reasoning-effort", default="low")
    parser.add_argument("--round-name", default="round1-formalization-sketch-and-context-needs")
    parser.add_argument("--max-context-tokens-per-record", type=int, default=4000)
    parser.add_argument("--openrouter-timeout", type=float, default=180.0)
    parser.add_argument("--max-actual-cost-usd", type=float, default=0.25)
    parser.add_argument("--budget-only", action="store_true")
    parser.add_argument("--hydrate-mathlib", action="store_true")
    parser.add_argument("--compare-gold", action="store_true")
    parser.add_argument("--mathlib-workspace", type=Path, default=None)
    parser.add_argument("--max-mathlib-results-per-query", type=int, default=3)
    parser.add_argument("--no-live-catalog-prices", action="store_true")
    parser.add_argument(
        "--reuse-existing-responses",
        action="store_true",
        help="Do not call OpenRouter for a batch when context-selection-response.json already exists.",
    )
    args = parser.parse_args()
    args.use_live_catalog_prices = not args.no_live_catalog_prices
    return args


if __name__ == "__main__":
    summary = run(parse_args())
    print(json.dumps({key: value for key, value in summary.items() if key != "results"}, indent=2))
