"""A stand-in for the Anthropic API. Records every request; never touches the network."""

import json
from collections.abc import Awaitable, Callable
from typing import Any

Responder = Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]


def message(text: str, stop_reason: str = "end_turn") -> dict[str, Any]:
    return {
        "id": "msg_fake",
        "type": "message",
        "role": "assistant",
        "model": "claude-opus-5-5",
        "content": [{"type": "thinking", "thinking": "", "signature": "sig"}, {"type": "text", "text": text}],
        "stop_reason": stop_reason,
        "usage": {"input_tokens": 600, "output_tokens": 40},
    }


def matches(*pairs: tuple[str, str]) -> dict[str, Any]:
    return message(json.dumps({"matches": [{"condition_id": c, "confidence": k} for c, k in pairs]}))


async def _default(request: dict[str, Any]) -> dict[str, Any]:
    return matches(("prediabetes", "high"), ("acid_reflux_or_gerd", "medium"))


class FakeTransport:
    def __init__(self) -> None:
        self.requests: list[dict[str, Any]] = []
        self.responder: Responder = _default

    async def send(self, request: dict[str, Any]) -> dict[str, Any]:
        self.requests.append(json.loads(json.dumps(request)))
        return await self.responder(request)
