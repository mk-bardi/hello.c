"""
accountability.py — Evening check-in and streak tracking: /checkin
ConversationHandler: study → leetcode → robotics → notes → summary
Uses inline Yes/No buttons for clean UX.
"""

import logging
from datetime import datetime

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from bardi_bot.ai_helper import get_motivational_response
from bardi_bot.config import TIMEZONE
from bardi_bot.database import update_streaks, upsert_daily_log

logger = logging.getLogger(__name__)

# ConversationHandler states (unique range: 300-309)
ASK_STUDY = 300
ASK_LEETCODE = 301
ASK_ROBOTICS = 302
ASK_NOTES = 303

_YES_NO_KB = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("✅ Yes", callback_data="yn_yes"),
        InlineKeyboardButton("❌ No", callback_data="yn_no"),
    ]
])


def _yn(data: str) -> bool:
    return data == "yn_yes"


async def checkin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_text(
        "🌙 *Evening Check-In*\n\nDid you study today?",
        parse_mode="Markdown",
        reply_markup=_YES_NO_KB,
    )
    return ASK_STUDY


async def receive_study(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data["study_done"] = _yn(query.data)
    label = "✅ Yes" if context.user_data["study_done"] else "❌ No"
    await query.edit_message_text(
        f"Study: {label}\n\nDid you do LeetCode today?",
        reply_markup=_YES_NO_KB,
    )
    return ASK_LEETCODE


async def receive_leetcode(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data["leetcode_done"] = _yn(query.data)
    label = "✅ Yes" if context.user_data["leetcode_done"] else "❌ No"
    await query.edit_message_text(
        f"LeetCode: {label}\n\nDid you do Robotics / ROS 2 today?",
        reply_markup=_YES_NO_KB,
    )
    return ASK_ROBOTICS


async def receive_robotics(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data["robotics_done"] = _yn(query.data)
    label = "✅ Yes" if context.user_data["robotics_done"] else "❌ No"
    await query.edit_message_text(
        f"Robotics: {label}\n\n"
        "Any notes? (What did you complete? What failed?)\n"
        "Type your notes or send `skip` to finish.",
    )
    return ASK_NOTES


async def receive_notes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    raw = update.message.text.strip()
    notes = None if raw.lower() in ("skip", "none", "-") else raw

    study = context.user_data.get("study_done", False)
    leetcode = context.user_data.get("leetcode_done", False)
    robotics = context.user_data.get("robotics_done", False)

    today = datetime.now(TIMEZONE).date().isoformat()

    await upsert_daily_log(user_id, today, study, leetcode, robotics, notes)
    streaks = await update_streaks(user_id, study, leetcode, robotics)

    # Build summary
    def icon(val: bool) -> str:
        return "✅" if val else "❌"

    def flame(n: int) -> str:
        return f"🔥 {n} day streak" if n > 0 else "Streak reset"

    summary = (
        f"📊 *Tonight's Log*\n\n"
        f"📚 Study:    {icon(study)}  — {flame(streaks['study_streak'])}\n"
        f"💻 LeetCode: {icon(leetcode)} — {flame(streaks['leetcode_streak'])}\n"
        f"🤖 Robotics: {icon(robotics)} — {flame(streaks['robotics_streak'])}\n"
    )
    if notes:
        summary += f"\n📝 Notes: _{notes}_\n"

    # Generate motivational close
    done_count = sum([study, leetcode, robotics])
    context_text = (
        f"Bardi completed {done_count}/3 goals today. "
        f"Study: {'yes' if study else 'no'}, "
        f"LeetCode: {'yes' if leetcode else 'no'}, "
        f"Robotics: {'yes' if robotics else 'no'}."
    )
    motivation = await get_motivational_response(context_text)

    summary += f"\n💥 _{motivation}_"

    await update.message.reply_text(summary, parse_mode="Markdown")

    context.user_data.clear()
    return ConversationHandler.END


async def cancel_checkin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_text("Check-in cancelled. Don't skip it tomorrow.")
    return ConversationHandler.END


def _build_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CommandHandler("checkin", checkin_command)],
        states={
            ASK_STUDY: [CallbackQueryHandler(receive_study, pattern=r"^yn_")],
            ASK_LEETCODE: [CallbackQueryHandler(receive_leetcode, pattern=r"^yn_")],
            ASK_ROBOTICS: [CallbackQueryHandler(receive_robotics, pattern=r"^yn_")],
            ASK_NOTES: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_notes)],
        },
        fallbacks=[CommandHandler("cancel", cancel_checkin)],
        name="checkin_conv",
        persistent=False,
    )


def register(application: Application) -> None:
    application.add_handler(_build_handler())
