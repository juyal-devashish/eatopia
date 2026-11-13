"""A keyword matcher that stands in for Claude when `LLM_TRANSPORT=offline`.

Used by the end-to-end tests (which must never call a paid API) and for running the demo locally without a key.
It answers in the same shape as a real structured-output response, picking listed options whose label words
appear in the member's text. It is not a model and is never used in production.
"""

import json
import re
from typing import Any

OFFLINE_MODEL = "offline-keyword-matcher"
OFFLINE_SUMMARY = (
    "Offline stand-in summary, not written by a model. Height {{height}}, weight {{weight}}, "
    "about {{steps}} steps a day. See the answers below for goals and food context."
)
_STOP = {"and", "or", "the", "with", "my", "of", "a", "an", "to", "in", "on", "more", "less", "some", "else"}


def _words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z]+", text.lower()) if len(w) > 3 and w not in _STOP}


class OfflineTransport:
    async def send(self, request: dict[str, Any]) -> dict[str, Any]:
        content: str = request["messages"][0]["content"]
        if "<answers>" in content:
            return self._reply({"summary": OFFLINE_SUMMARY})
        member = _words(content.split("<member_text>", 1)[1])
        listing = re.search(r"<(conditions|options)>\n(.*?)\n</\1>", content, re.S)
        matches = []
        for line in listing.group(2).splitlines() if listing else []:
            choice_id, _, label = line.partition(": ")
            if _words(label) & member:
                matches.append({"id": choice_id, "confidence": "medium"})
        return self._reply({"matches": matches[:3]})

    @staticmethod
    def _reply(payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": "msg_offline",
            "type": "message",
            "role": "assistant",
            "model": OFFLINE_MODEL,
            "content": [{"type": "text", "text": json.dumps(payload)}],
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 0, "output_tokens": 0},
        }
