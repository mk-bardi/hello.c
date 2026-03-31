"""
focus.py — Pomodoro study timer: /focus (50 min work + 10 min break), /stopfocus
"""

import asyncio
import logging

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from bardi_bot.config import POMODORO_BREAK_SEC, POMODORO_WORK_SEC

logger = logging.getLogger(__name__)

_FOCUS_KEY = "focus_task_{user_id}"


def _key(user_id: int) -> str:
    return f"focus_task_{user_id}"


async def _run_focus_timer(bot, chat_id: int, user_id: int, bot_data: dict) -> None:
    """The async task that runs the Pomodoro timer."""
    try:
        await asyncio.sleep(POMODORO_WORK_SEC)
        await bot.send_message(
            chat_id=chat_id,
            text=(
                "⏸ *50 minutes done.*\n\n"
                "Take a 10-minute break. Walk. Breathe. Hydrate.\n"
                "I'll call you back."
            ),
            parse_mode="Markdown",
        )
        await asyncio.sleep(POMODORO_BREAK_SEC)
        await bot.send_message(
            chat_id=chat_id,
            text=(
                "▶️ *Break over. Back to work.*\n\n"
                "Type /focus to start another session."
            ),
            parse_mode="Markdown",
        )
    except asyncio.CancelledError:
        # /stopfocus was called
        pass
    finally:
        bot_data.pop(_key(user_id), None)


async def focus_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    key = _key(user_id)

    if key in context.bot_data:
        await update.message.reply_text(
            "You already have an active focus session. "
            "Use /stopfocus to cancel it first."
        )
        return

    await update.message.reply_text(
        "🔒 *Focus mode ON.*\n\n"
        "No distractions. Start now.\n"
        f"I'll check back in {POMODORO_WORK_SEC // 60} minutes.",
        parse_mode="Markdown",
    )

    task = asyncio.create_task(
        _run_focus_timer(context.bot, update.effective_chat.id, user_id, context.bot_data)
    )
    context.bot_data[key] = task


async def stopfocus_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    key = _key(user_id)
    task: asyncio.Task | None = context.bot_data.get(key)

    if task is None:
        await update.message.reply_text("No active focus session to stop.")
        return

    task.cancel()
    context.bot_data.pop(key, None)
    await update.message.reply_text(
        "🛑 Focus session cancelled.\n\n"
        "_You stopped it. Make sure it was worth it._",
        parse_mode="Markdown",
    )


def register(application: Application) -> None:
    application.add_handler(CommandHandler("focus", focus_command))
    application.add_handler(CommandHandler("stopfocus", stopfocus_command))
