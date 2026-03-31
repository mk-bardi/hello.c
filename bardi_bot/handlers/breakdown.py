"""
breakdown.py — AI-powered ADHD task breakdown: /breakdown
ConversationHandler: ask for task name → GPT-4o-mini decomposition.
"""

import logging

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ConversationHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from bardi_bot.ai_helper import breakdown_task

logger = logging.getLogger(__name__)

# ConversationHandler state (unique range: 200-209)
AWAIT_TASK_NAME = 200


async def breakdown_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "🧠 *Task Breakdown*\n\nWhat task do you want me to break down?",
        parse_mode="Markdown",
    )
    return AWAIT_TASK_NAME


async def receive_task_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    task_name = update.message.text.strip()
    thinking_msg = await update.message.reply_text("⚙️ Breaking it down with AI...")

    steps = await breakdown_task(task_name)

    await thinking_msg.delete()
    await update.message.reply_text(
        f"📋 *{task_name}*\n\n{steps}\n\n"
        "---\n"
        "Ready to start? Type /focus to begin a 50-min session.",
        parse_mode="Markdown",
    )
    return ConversationHandler.END


async def cancel_breakdown(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Breakdown cancelled.")
    return ConversationHandler.END


def _build_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CommandHandler("breakdown", breakdown_command)],
        states={
            AWAIT_TASK_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_task_name)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_breakdown)],
        name="breakdown_conv",
        persistent=False,
    )


def register(application: Application) -> None:
    application.add_handler(_build_handler())
