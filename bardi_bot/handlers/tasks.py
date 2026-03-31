"""
tasks.py — Task management: /addtask (ConversationHandler), /done, /overdue
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

from bardi_bot.config import TIMEZONE
from bardi_bot.database import (
    add_task,
    get_all_pending_tasks,
    get_overdue_tasks,
    get_today_tasks,
    mark_task_done,
)

logger = logging.getLogger(__name__)

# ConversationHandler states (unique range: 100-109)
TASK_TEXT = 100
TASK_PRIORITY = 101
TASK_DUE_DATE = 102

_PRIORITY_KB = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("🔴 High", callback_data="prio_High"),
        InlineKeyboardButton("🟡 Medium", callback_data="prio_Medium"),
        InlineKeyboardButton("🟢 Low", callback_data="prio_Low"),
    ]
])


# ---------------------------------------------------------------------------
# /addtask conversation
# ---------------------------------------------------------------------------
async def addtask_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "📝 *New Task*\n\nWhat's the task? Type it now.",
        parse_mode="Markdown",
    )
    return TASK_TEXT


async def receive_task_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["task_text"] = update.message.text.strip()
    await update.message.reply_text(
        "Priority?",
        reply_markup=_PRIORITY_KB,
    )
    return TASK_PRIORITY


async def receive_task_priority(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    priority = query.data.replace("prio_", "")
    context.user_data["task_priority"] = priority
    await query.edit_message_text(
        f"Priority set: *{priority}*\n\n"
        "Due date? Type `today`, `tomorrow`, a date like `2026-04-15`, or `none` to skip.",
        parse_mode="Markdown",
    )
    return TASK_DUE_DATE


async def receive_task_due_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    raw = update.message.text.strip().lower()
    today = datetime.now(TIMEZONE).date()

    if raw in ("none", "skip", "-"):
        due_date = None
    elif raw == "today":
        due_date = today.isoformat()
    elif raw == "tomorrow":
        from datetime import timedelta
        due_date = (today + timedelta(days=1)).isoformat()
    else:
        try:
            datetime.strptime(raw, "%Y-%m-%d")
            due_date = raw
        except ValueError:
            await update.message.reply_text(
                "Invalid date format. Use `YYYY-MM-DD`, `today`, `tomorrow`, or `none`.",
                parse_mode="Markdown",
            )
            return TASK_DUE_DATE

    task_text = context.user_data.pop("task_text", "Untitled task")
    priority = context.user_data.pop("task_priority", "Medium")

    task_id = await add_task(user_id, task_text, priority, due_date)
    due_label = due_date if due_date else "No due date"
    priority_icon = {"High": "🔴", "Medium": "🟡", "Low": "🟢"}.get(priority, "⚪")

    await update.message.reply_text(
        f"✅ Task added (ID: {task_id})\n"
        f"{priority_icon} *{task_text}*\n"
        f"Due: {due_label}",
        parse_mode="Markdown",
    )
    return ConversationHandler.END


async def cancel_addtask(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.pop("task_text", None)
    context.user_data.pop("task_priority", None)
    await update.message.reply_text("Task entry cancelled.")
    return ConversationHandler.END


# ---------------------------------------------------------------------------
# /done
# ---------------------------------------------------------------------------
async def done_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    tasks = await get_all_pending_tasks(user_id)
    if not tasks:
        await update.message.reply_text("No pending tasks. You're clear! 🎉")
        return

    keyboard = []
    for t in tasks[:20]:  # cap at 20 buttons
        priority_icon = {"High": "🔴", "Medium": "🟡", "Low": "🟢"}.get(t["priority"], "⚪")
        label = f"{priority_icon} [{t['id']}] {t['text'][:35]}"
        keyboard.append([InlineKeyboardButton(label, callback_data=f"done_{t['id']}")])

    await update.message.reply_text(
        "Which task did you complete?",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def done_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    task_id = int(query.data.replace("done_", ""))
    success = await mark_task_done(task_id, user_id)
    if success:
        await query.edit_message_text(f"✅ Task {task_id} marked as done. Keep going.")
    else:
        await query.edit_message_text("Task not found or already completed.")


# ---------------------------------------------------------------------------
# /overdue
# ---------------------------------------------------------------------------
async def overdue_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    tasks = await get_overdue_tasks(user_id)
    if not tasks:
        await update.message.reply_text("✅ No overdue tasks. Good discipline.")
        return

    lines = [f"⚠️ *Overdue Tasks* ({len(tasks)} total)\n"]
    for t in tasks:
        priority_icon = {"High": "🔴", "Medium": "🟡", "Low": "🟢"}.get(t["priority"], "⚪")
        lines.append(f"  {priority_icon} [{t['id']}] {t['text']} — due {t['due_date']}")

    lines.append("\nUse /done to check them off, or they'll carry over to today.")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------
def _build_addtask_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CommandHandler("addtask", addtask_command)],
        states={
            TASK_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_task_text)],
            TASK_PRIORITY: [CallbackQueryHandler(receive_task_priority, pattern=r"^prio_")],
            TASK_DUE_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_task_due_date)],
        },
        fallbacks=[CommandHandler("cancel", cancel_addtask)],
        name="addtask_conv",
        persistent=False,
    )


def register(application: Application) -> None:
    application.add_handler(_build_addtask_handler())
    application.add_handler(CommandHandler("done", done_command))
    application.add_handler(CallbackQueryHandler(done_callback, pattern=r"^done_\d+$"))
    application.add_handler(CommandHandler("overdue", overdue_command))
