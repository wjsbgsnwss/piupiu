from __future__ import annotations
import logging

import anthropic

from ._context import format_context
from .base import AIProvider, Entity, ExtractionResult, Relationship
from .prompts import PROCESS_TOOL, SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class ClaudeProvider:
    """AI provider backed by the Anthropic Claude API."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-6") -> None:
        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        self._model = model

    async def process(self, message: str, context: list[dict]) -> ExtractionResult:
        user_content = message
        ctx = format_context(context)
        if ctx:
            user_content += f"\n\n[Graph context]\n{ctx}"

        response = await self._client.messages.create(
            model=self._model,
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            tools=[PROCESS_TOOL],
            tool_choice={"type": "auto"},
            messages=[{"role": "user", "content": user_content}],
        )

        for block in response.content:
            if block.type == "tool_use" and block.name == "process_message":
                d = block.input
                return ExtractionResult(
                    entities=[Entity(**e) for e in d.get("entities", [])],
                    relationships=[Relationship(**r) for r in d.get("relationships", [])],
                    intent=d.get("intent", "chat"),
                    response=d.get("response", ""),
                )

        # Fallback: model replied in plain text without using the tool
        text = next((b.text for b in response.content if hasattr(b, "text")), "")
        logger.warning("Claude did not use the tool — falling back to plain text response")
        return ExtractionResult(entities=[], relationships=[], intent="chat", response=text)
