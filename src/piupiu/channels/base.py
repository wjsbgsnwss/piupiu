from dataclasses import dataclass, field
from typing import Callable, Awaitable, Protocol


@dataclass
class Message:
    text: str
    sender_id: str
    chat_id: str
    message_id: str = ""
    channel: str = ""


MessageHandler = Callable[[Message], Awaitable[None]]


class Channel(Protocol):
    async def start(self) -> None: ...
    async def stop(self) -> None: ...
    async def send(self, chat_id: str, text: str) -> None: ...
