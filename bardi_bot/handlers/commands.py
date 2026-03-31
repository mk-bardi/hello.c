"""
commands.py — Core bot commands: /start, /help, /today, /streak, /motivate, /weekly
"""

import logging
from datetime import datetime, timedelta

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from bardi_bot.config import (
    TIMEZONE,
    format_lecture_block,
    get_random_quote,
    get_today_lectures,
    get_upcoming_exams,
    build_study_schedule,
)
from bardi_bot.database import (
    get_streaks,
    get_today_tasks,
    get_weekly_logs,
    get_weekly_task_summary,
)

logger = logging.getLogger(__name__)

HELP_TEXT = """
*Bardi Assistant — Command Reference*

*Daily*
/today — Today's schedule, lectures & tasks
/motivate — Get a push when you need it

*Tasks*
/addtask — Add a new task (guided)
/done — Mark a task as complete
/overdue — View overdue tasks

*Focus*
/focus — Start 50-min Pomodoro session
/stopfocus — Cancel active focus session

*Learning*
/breakdown — AI-powered task breakdown

*Accountability*
/checkin — Evening check-in (study/LeetCode/robotics)
/streak — View your current streaks

*Weekly*
/weekly — This week's summary & reset

/help — Show this message
""".strip()


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "👋 *Bardi Assistant Online.*\n\n"
        "I'm your personal AI executive assistant. I enforce structure, track your progress, "
        "and won't let you slack.\n\n"
        "Here's what I can do:\n"
        + HELP_TEXT
        + "\n\n_Type /today to see what's on for today._"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(HELP_TEXT, parse_mode="Markdown")


async def today_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    today = datetime.now(TIMEZONE).strftime("%A, %d %B %Y")

    lectures = get_today_lectures()
    lecture_block = format_lecture_block(lectures)
    study_block = build_study_schedule(lectures)

    tasks = await get_today_tasks(user_id)
    if tasks:
        task_lines = []
        for t in tasks:
            priority_icon = {"High": "🔴", "Medium": "🟡", "Low": "🟢"}.get(t["priority"], "⚪")
            task_lines.append(f"  {priority_icon} [{t['id']}] {t['text']}")
        task_block = "📋 *Today's Tasks*\n" + "\n".join(task_lines)
    else:
        task_block = "📋 *No tasks for today.* Add one with /addtask"

    upcoming = get_upcoming_exams()
    if upcoming:
        exam_lines = [f"  ⚠️ {e['course']} — {e['days_left']} day(s) away" for e in upcoming]
        exam_block = "🎓 *Upcoming Exams*\n" + "\n".join(exam_lines)
    else:
        exam_block = ""

    parts = [f"📆 *{today}*\n", lecture_block, study_block, task_block]
    if exam_block:
        parts.append("\n" + exam_block)

    await update.message.reply_text("\n".join(parts), parse_mode="Markdown")


async def streak_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    s = await get_streaks(user_id)

    def flame(n: int) -> str:
        return "🔥" * min(n, 7) if n > 0 else "❌"

    text = (
        "*Your Streaks*\n\n"
        f"📚 Study:    {s['study_streak']} day(s) {flame(s['study_streak'])}\n"
        f"💻 LeetCode: {s['leetcode_streak']} day(s) {flame(s['leetcode_streak'])}\n"
        f"🤖 Robotics: {s['robotics_streak']} day(s) {flame(s['robotics_streak'])}\n\n"
        "_Keep the streak alive. Miss one day and it resets._"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def motivate_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    quote = get_random_quote()
    await update.message.reply_text(f"💥 _{quote}_", parse_mode="Markdown")


async def weekly_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    today = datetime.now(TIMEZONE).date()
    start = (today - timedelta(days=6)).isoformat()
    end = today.isoformat()

    logs = await get_weekly_logs(user_id, start, end)
    summary = await get_weekly_task_summary(user_id, start)
    streaks = await get_streaks(user_id)

    study_days = sum(1 for l in logs if l["study_done"])
    leet_days = sum(1 for l in logs if l["leetcode_done"])
    robot_days = sum(1 for l in logs if l["robotics_done"])

    text = (
        "📊 *Weekly Summary*\n\n"
        f"📚 Study sessions: {study_days}/7 days\n"
        f"💻 LeetCode sessions: {leet_days}/7 days\n"
        f"🤖 Robotics sessions: {robot_days}/7 days\n\n"
        f"✅ Tasks completed: {summary['completed']}\n"
        f"❌ Tasks missed: {summary['missed']}\n\n"
        f"*Current Streaks*\n"
        f"Study: {streaks['study_streak']} 🔥 | "
        f"LeetCode: {streaks['leetcode_streak']} 🔥 | "
        f"Robotics: {streaks['robotics_streak']} 🔥\n\n"
    )

    if summary["missed"] > 3:
        text += "⚠️ Too many missed tasks. Plan better this week.\n"
    elif summary["completed"] >= 5:
        text += "✅ Solid week. Keep the momentum.\n"
    else:
        text += "📈 Room to improve. Set 3 clear goals for this week.\n"

    await update.message.reply_text(text, parse_mode="Markdown")


def register(application: Application) -> None:
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("today", today_command))
    application.add_handler(CommandHandler("streak", streak_command))
    application.add_handler(CommandHandler("motivate", motivate_command))
    application.add_handler(CommandHandler("weekly", weekly_command))
