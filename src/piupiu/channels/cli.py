from __future__ import annotations
import asyncio
import select
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

    async def confirm(self, chat_id: str, message: str, timeout: int) -> bool:
        print(f"\n{message}")
        print(f"\nAccept? [Y/n] (auto-accepts in {timeout}s): ", end="", flush=True)
        deadline = asyncio.get_event_loop().time() + timeout
        while True:
            remaining = deadline - asyncio.get_event_loop().time()
            if remaining <= 0:
                print("\nAuto-accepted.")
                return True
            ready, _, _ = select.select([sys.stdin], [], [], min(remaining, 0.1))
            if ready:
                response = sys.stdin.readline().strip().lower()
                accepted = response not in ("n", "no", "reject")
                print("Accepted." if accepted else "Rejected.")
                return accepted
            await asyncio.sleep(0.05)
