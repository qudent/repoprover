#!/usr/bin/env python3
"""Estimate OpenRouter spend from RepoProver run token logs.

The script reads the same JSONL recordings used by count_tokens.py, fetches
current OpenRouter model prices when requested, and prints a compact budget
projection for one or more models.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from count_tokens import AgentTokenStats, analyze_run, find_all_runs


DEFAULT_MODELS = [
    "deepseek/deepseek-v4-pro",
    "qwen/qwen3-coder",
    "qwen/qwen3-coder-plus",
    "z-ai/glm-5",
    "z-ai/glm-5.1",
    "google/gemini-2.5-flash",
]


@dataclass(frozen=True)
class ModelPrice:
    model: str
    context_length: int | None
    input_per_token: float
    output_per_token: float

    @property
    def input_per_million(self) -> float:
        return self.input_per_token * 1_000_000

    @property
    def output_per_million(self) -> float:
        return self.output_per_token * 1_000_000


def fetch_json(url: str, api_key: str | None = None) -> dict[str, Any]:
    headers = {"User-Agent": "repoprover-budget-estimator"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_openrouter_prices(model_ids: list[str]) -> dict[str, ModelPrice]:
    data = fetch_json("https://openrouter.ai/api/v1/models")
    by_id = {entry.get("id"): entry for entry in data.get("data", [])}

    prices: dict[str, ModelPrice] = {}
    missing: list[str] = []
    for model_id in model_ids:
        entry = by_id.get(model_id)
        if not entry:
            missing.append(model_id)
            continue
        pricing = entry.get("pricing", {})
        prices[model_id] = ModelPrice(
            model=model_id,
            context_length=entry.get("context_length"),
            input_per_token=float(pricing.get("prompt", 0.0)),
            output_per_token=float(pricing.get("completion", 0.0)),
        )
    if missing:
        print(f"warning: model(s) not found in OpenRouter catalog: {', '.join(missing)}", file=sys.stderr)
    return prices


def fetch_openrouter_credits(api_key: str | None) -> float | None:
    if not api_key:
        return None
    try:
        data = fetch_json("https://openrouter.ai/api/v1/credits", api_key=api_key)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        print(f"warning: could not fetch OpenRouter credits: {exc}", file=sys.stderr)
        return None

    credit_data = data.get("data", {})
    total_credits = float(credit_data.get("total_credits", 0.0))
    total_usage = float(credit_data.get("total_usage", 0.0))
    return total_credits - total_usage


def selected_agents(stats: list[AgentTokenStats], agent_types: set[str], outcomes: set[str]) -> list[AgentTokenStats]:
    agents = stats
    if agent_types:
        agents = [agent for agent in agents if agent.agent_type in agent_types]
    if outcomes:
        agents = [agent for agent in agents if agent.outcome.value in outcomes]
    return agents


def estimate_cost(agents: list[AgentTokenStats], price: ModelPrice, multiplier: float) -> dict[str, float]:
    input_tokens = sum(agent.input_tokens for agent in agents) * multiplier
    output_tokens = sum(agent.output_tokens for agent in agents) * multiplier
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost": input_tokens * price.input_per_token + output_tokens * price.output_per_token,
    }


def format_money(value: float) -> str:
    return f"${value:,.4f}" if value < 1 else f"${value:,.2f}"


def print_markdown(
    prices: dict[str, ModelPrice],
    agents: list[AgentTokenStats],
    budgets: list[float],
    multiplier: float,
    observed_credits: float | None,
) -> None:
    input_tokens = sum(agent.input_tokens for agent in agents) * multiplier
    output_tokens = sum(agent.output_tokens for agent in agents) * multiplier

    print("# OpenRouter Budget Estimate")
    print()
    print(f"Baseline agents: {len(agents)}")
    print(f"Baseline tokens: {input_tokens:,.0f} input / {output_tokens:,.0f} output")
    print(f"Multiplier: {multiplier:g}x")
    if observed_credits is not None:
        print(f"Observed key balance: {format_money(observed_credits)}")
    print()
    print("| Model | Context | Price in/out per M | Baseline cost | Runs in budgets |")
    print("|---|---:|---:|---:|---:|")
    for model_id, price in prices.items():
        est = estimate_cost(agents, price, multiplier)
        if est["cost"] <= 0:
            runs = "n/a"
        else:
            runs = ", ".join(f"{format_money(b)}={b / est['cost']:.1f}x" for b in budgets)
        context = f"{price.context_length:,}" if price.context_length else "unknown"
        print(
            f"| `{model_id}` | {context} | "
            f"${price.input_per_million:g}/${price.output_per_million:g} | "
            f"{format_money(est['cost'])} | {runs} |"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path, help="Formalization repo, runs directory, or individual run")
    parser.add_argument("--model", action="append", dest="models", help="OpenRouter model id; repeatable")
    parser.add_argument("--budget", action="append", type=float, default=[], help="Budget in dollars; repeatable")
    parser.add_argument(
        "--agent-type",
        action="append",
        default=[],
        help="Only include this agent type, e.g. sketch or math_reviewer; repeatable",
    )
    parser.add_argument(
        "--outcome",
        action="append",
        default=[],
        help="Only include this outcome, e.g. merged or no_pr; repeatable",
    )
    parser.add_argument(
        "--multiplier",
        type=float,
        default=1.0,
        help="Scale observed baseline tokens for larger chapters/extra rounds",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of Markdown")
    parser.add_argument(
        "--no-live-credits",
        action="store_true",
        help="Do not query the authenticated OpenRouter credits endpoint",
    )
    args = parser.parse_args()

    runs = find_all_runs(args.path)
    if not runs:
        print(f"error: no RepoProver runs found under {args.path}", file=sys.stderr)
        return 1

    all_agents: list[AgentTokenStats] = []
    for run in runs:
        all_agents.extend(analyze_run(run).agents.values())

    agents = selected_agents(all_agents, set(args.agent_type), set(args.outcome))
    if not agents:
        print("error: filters selected zero agents", file=sys.stderr)
        return 1

    model_ids = args.models or DEFAULT_MODELS
    prices = fetch_openrouter_prices(model_ids)
    if not prices:
        print("error: no model prices available", file=sys.stderr)
        return 1

    budgets = args.budget or [10.0, 50.0]
    observed_credits = None
    if not args.no_live_credits:
        observed_credits = fetch_openrouter_credits(os.environ.get("OPENROUTER_API_KEY"))

    if args.json:
        output = {
            "baseline": {
                "agents": len(agents),
                "input_tokens": sum(agent.input_tokens for agent in agents) * args.multiplier,
                "output_tokens": sum(agent.output_tokens for agent in agents) * args.multiplier,
                "multiplier": args.multiplier,
                "observed_credits": observed_credits,
            },
            "models": {
                model_id: {
                    **estimate_cost(agents, price, args.multiplier),
                    "context_length": price.context_length,
                    "input_per_million": price.input_per_million,
                    "output_per_million": price.output_per_million,
                    "budget_runs": {
                        str(budget): (budget / estimate_cost(agents, price, args.multiplier)["cost"])
                        for budget in budgets
                        if estimate_cost(agents, price, args.multiplier)["cost"] > 0
                    },
                }
                for model_id, price in prices.items()
            },
        }
        print(json.dumps(output, indent=2))
    else:
        print_markdown(prices, agents, budgets, args.multiplier, observed_credits)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
