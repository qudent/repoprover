from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any

from openai.types.chat import ChatCompletionMessageToolCall

from repoprover.agents.tools import run_tool_loop


class _FakeChatCompletions:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        if len(self.calls) == 1:
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        finish_reason="tool_calls",
                        message=SimpleNamespace(
                            content=None,
                            tool_calls=[
                                ChatCompletionMessageToolCall(
                                    id="call_1",
                                    type="function",
                                    function={"name": "echo", "arguments": json.dumps({"text": "hello"})},
                                    extra_content={"google": {"thought_signature": "signed-reasoning"}},
                                )
                            ],
                        ),
                    )
                ],
                usage=None,
            )

        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    finish_reason="stop",
                    message=SimpleNamespace(content="done", tool_calls=None),
                )
            ],
            usage=None,
        )


class _FakeClient:
    def __init__(self) -> None:
        completions = _FakeChatCompletions()
        self.completions = completions
        self.chat = SimpleNamespace(completions=completions)


class _RepeatingToolErrorChatCompletions:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    finish_reason="tool_calls",
                    message=SimpleNamespace(
                        content=None,
                        tool_calls=[
                            ChatCompletionMessageToolCall(
                                id=f"call_{len(self.calls)}",
                                type="function",
                                function={
                                    "name": "lean_check",
                                    "arguments": json.dumps({"code": "{'n': 'Nat'}"}),
                                },
                            )
                        ],
                    ),
                )
            ],
            usage=None,
        )


class _RepeatingToolErrorClient:
    def __init__(self) -> None:
        completions = _RepeatingToolErrorChatCompletions()
        self.completions = completions
        self.chat = SimpleNamespace(completions=completions)


def test_tool_loop_preserves_provider_tool_call_metadata() -> None:
    client = _FakeClient()

    result = run_tool_loop(
        client=client,  # type: ignore[arg-type]
        model="gemini-3-flash-preview",
        system_prompt="You are a test assistant.",
        initial_messages=[{"role": "user", "content": "call echo"}],
        tools=[
            {
                "type": "function",
                "function": {
                    "name": "echo",
                    "description": "Echo text.",
                    "parameters": {
                        "type": "object",
                        "properties": {"text": {"type": "string"}},
                        "required": ["text"],
                    },
                },
            }
        ],
        tool_handler=lambda _name, args: args["text"],
        max_iterations=2,
    )

    assert result.stop_reason == "stop"
    assert len(client.completions.calls) == 2

    second_request_messages = client.completions.calls[1]["messages"]
    assistant_messages = [msg for msg in second_request_messages if msg["role"] == "assistant"]
    assert assistant_messages
    assert assistant_messages[-1]["tool_calls"][0]["extra_content"] == {
        "google": {"thought_signature": "signed-reasoning"}
    }


def test_tool_loop_stops_after_repeated_identical_tool_errors() -> None:
    client = _RepeatingToolErrorClient()

    result = run_tool_loop(
        client=client,  # type: ignore[arg-type]
        model="qwen/qwen3-coder",
        system_prompt="You are a test assistant.",
        initial_messages=[{"role": "user", "content": "prove the theorem"}],
        tools=[
            {
                "type": "function",
                "function": {
                    "name": "lean_check",
                    "description": "Check Lean code.",
                    "parameters": {
                        "type": "object",
                        "properties": {"code": {"type": "string"}},
                        "required": ["code"],
                    },
                },
            }
        ],
        tool_handler=lambda _name, _args: "## Compilation Errors (1)\n- unexpected token",
        max_iterations=10,
        max_consecutive_tool_errors=3,
    )

    assert result.stop_reason == "repeated_tool_error"
    assert result.iteration_count == 3
    assert len(result.tool_calls) == 3
    assert len(client.completions.calls) == 3
