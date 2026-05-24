from __future__ import annotations
import logging
from aiogram import Bot, Dispatcher, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import Message as TGMessage
from .base import Message, MessageHandler

logger = logging.getLogger(__name__)


class TelegramChannel:
    """Telegram channel adapter using aiogram 3.x."""

    def __init__(self, token: str, on_message: MessageHandler) -> None:
        self._bot = Bot(
            token=token,
            default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN),
        )
        self._dp = Dispatcher()
        self._router = Router()
        self._on_message = on_message
        self._register_handlers()
        self._dp.include_router(self._router)

    def _register_handlers(self) -> None:
        @self._router.message()
        async def handle(tg_msg: TGMessage) -> None:
            if not tg_msg.text:
                return
            msg = Message(
                text=tg_msg.text,
                sender_id=str(tg_msg.from_user.id) if tg_msg.from_user else "unknown",
                chat_id=str(tg_msg.chat.id),
                message_id=str(tg_msg.message_id),
                channel="telegram",
            )
            await self._on_message(msg)

    async def start(self) -> None:
        logger.info("Telegram polling started")
        await self._dp.start_polling(self._bot)

    async def stop(self) -> None:
        await self._dp.stop_polling()
        await self._bot.session.close()

    async def send(self, chat_id: str, text: str) -> None:
        # Escape characters that break Markdown in Telegram
        try:
            await self._bot.send_message(chat_id=int(chat_id), text=text)
        except Exception as exc:
            logger.warning("Failed to send Telegram message: %s", exc)
            # Retry as plain text if markdown parsing failed
            await self._bot.send_message(
                chat_id=int(chat_id), text=text, parse_mode=None
            )
