from __future__ import annotations
import asyncio
import logging
import uuid
from aiogram import Bot, Dispatcher, F, Router
from aiogram.types import (
    BotCommand, CallbackQuery,
    InlineKeyboardButton, InlineKeyboardMarkup,
    Message as TGMessage,
)
from .base import Message, MessageHandler

logger = logging.getLogger(__name__)


class TelegramChannel:
    """Telegram channel adapter using aiogram 3.x."""

    def __init__(self, token: str, on_message: MessageHandler) -> None:
        self._bot = Bot(token=token)
        self._dp = Dispatcher()
        self._router = Router()
        self._on_message = on_message
        self._pending_confirms: dict[str, asyncio.Future] = {}
        self._register_handlers()
        self._dp.include_router(self._router)

    def _register_handlers(self) -> None:
        @self._router.callback_query(F.data.startswith("confirm:"))
        async def handle_confirm_callback(cb: CallbackQuery) -> None:
            parts = (cb.data or "").split(":", 2)
            if len(parts) == 3:
                _, action, cid = parts
                fut = self._pending_confirms.get(cid)
                if fut and not fut.done():
                    fut.set_result(action == "accept")
            await cb.answer()

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
        await self._bot.set_my_commands([
            BotCommand(command="graph",  description="Show all nodes and edges in your knowledge graph"),
            BotCommand(command="show",   description="Look up nodes by name  e.g. /show pristine"),
            BotCommand(command="delete", description="Delete a node by name  e.g. /delete pristine"),
            BotCommand(command="help",   description="Show node types, examples, and available commands"),
        ])
        logger.info("Telegram polling started")
        await self._dp.start_polling(self._bot)

    async def stop(self) -> None:
        await self._dp.stop_polling()
        await self._bot.session.close()

    async def send(self, chat_id: str, text: str) -> None:
        await self._bot.send_message(chat_id=int(chat_id), text=text)

    async def confirm(self, chat_id: str, message: str, timeout: int) -> bool:
        cid = uuid.uuid4().hex[:8]
        fut: asyncio.Future[bool] = asyncio.get_event_loop().create_future()
        self._pending_confirms[cid] = fut

        keyboard = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="✓ Accept", callback_data=f"confirm:accept:{cid}"),
            InlineKeyboardButton(text="✗ Reject", callback_data=f"confirm:reject:{cid}"),
        ]])
        sent = await self._bot.send_message(
            chat_id=int(chat_id),
            text=f"{message}\n\nAuto-accepts in {timeout}s.",
            reply_markup=keyboard,
        )
        try:
            accepted = await asyncio.wait_for(asyncio.shield(fut), timeout=timeout)
            label = "Stored." if accepted else "Cancelled."
        except asyncio.TimeoutError:
            accepted = True
            label = "Auto-stored (no response)."
        finally:
            self._pending_confirms.pop(cid, None)

        await sent.edit_text(f"{message}\n\n{label}", reply_markup=None)
        return accepted
