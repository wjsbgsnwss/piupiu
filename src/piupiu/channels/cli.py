from __future__ import annotations
import asyncio
import sys
from .base import Message, MessageHandler


class CLIChannel:
    """stdin/stdout channel — useful for local development and testing."""

    def __init__(self, on_message: MessageHandler) -> None:
        self._on_message = on_message
        self._running = False

    async def start(self) -> None:
        self._running = True
        print("PiuPiu CLI ready — type your message (Ctrl+C or EOF to exit)\n")
        loop = asyncio.get_event_loop()
        while self._running:
            try:
                line: str = await loop.run_in_executor(None, sys.stdin.readline)
                if not line:
                    break
                text = line.strip()
                if not text:
                    continue
                await self._on_message(Message(
                    text=text,
                    sender_id="cli_user",
                    chat_id="cli",
                    channel="cli",
                ))
            except (KeyboardInterrupt, EOFError):
                break

    async def stop(self) -> None:
        self._running = False

    async def send(self, chat_id: str, text: str) -> None:
        print(f"\nPiuPiu: {text}\n")
