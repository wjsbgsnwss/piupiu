from __future__ import annotations
import json
import logging
import httpx
from ._context import format_context
from .base import AIProvider, ExtractionResult, parse_extraction
from .prompts import SYSTEM_PROMPT, PROCESS_TOOL_OPENAI

logger = logging.getLogger(__name__)

NIM_BASE_URL = "https://integrate.api.nvidia.com/v1"


class NIMProvider:
    """AI provider backed by NVIDIA NIM (OpenAI-compatible API)."""

    def __init__(
        self,
        api_key: str,
        model: str = "meta/llama-3.1-70b-instruct",
        base_url: str = NIM_BASE_URL,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._base_url = base_url.rstrip("/")

    async def process(self, message: str, context: list[dict]) -> ExtractionResult:
        user_content = message
        ctx = format_context(context)
        if ctx:
            user_content += f"\n\n[Graph context]\n{ctx}"

        logger.debug(
            "── Sending to NIM (%s) ─────────────────────────\n%s\n──────────────────────────────────────────────────",
            self._model, user_content,
        )

        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            "tools": [PROCESS_TOOL_OPENAI],
            "tool_choice": "auto",
            "max_tokens": 2048,
        }

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{self._base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

        choice = data["choices"][0]["message"]

        # Tool call response
        tool_calls = choice.get("tool_calls") or []
        for call in tool_calls:
            if call.get("function", {}).get("name") == "process_message":
                return parse_extraction(json.loads(call["function"]["arguments"]))

        # Fallback: plain text response (model skipped tool use)
        text = choice.get("content") or ""
        logger.warning("NIM model did not use the tool — falling back to plain text")
        return ExtractionResult(entities=[], relationships=[], intent="chat", response=text)
