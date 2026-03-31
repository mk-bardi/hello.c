"""
scheduler.py — APScheduler cron jobs for Bardi Assistant.
All jobs send messages via application.bot.send_message(chat_id=CHAT_ID, ...).
Call start_scheduler(application) once at bot startup.
"""

import logging
import os
from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram.ext import Application

from bardi_bot.config import (
    EXAM_COUNTDOWN_HOUR,
    EXAM_COUNTDOWN_MINUTE,
    EVENING_CHECKIN_HOUR,
    EVENING_CHECKIN_MINUTE,
    LECTURE_SCHEDULE,
    MORNING_SCHEDULE_HOUR,
    MORNING_SCHEDULE_MINUTE,
    TIMEZONE,
    WEEKLY_RESET_HOUR,
    WEEKLY_RESET_MINUTE,
    build_study_schedule,
    format_lecture_block,
    get_random_quote,
    get_today_lectures,
    get_upcoming_exams,
    reminder_time,
)
from bardi_bot.database import carry_over_overdue, get_streaks, get_today_tasks, get_weekly_task_summary

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone=TIMEZONE)


def _chat_id() -> int:
    val = os.getenv("CHAT_ID", "")
    if not val:
        raise RuntimeError("CHAT_ID environment variable is not set.")
    return int(val)


# ---------------------------------------------------------------------------
# Job: Morning Schedule (06:00 daily)
# ---------------------------------------------------------------------------
async def job_morning_schedule(app: Application) -> None:
    try:
        chat_id = _chat_id()
        today = datetime.now(TIMEZONE).strftime("%A, %d %B %Y")
        lectures = get_today_lectures()

        # Carry over overdue tasks
        carried = await carry_over_overdue(chat_id)

        lecture_block = format_lecture_block(lectures)
        study_block = build_study_schedule(lectures)

        tasks = await get_today_tasks(chat_id)
        if tasks:
            task_lines = []
            for t in tasks:
                icon = {"High": "🔴", "Medium": "🟡", "Low": "🟢"}.get(t["priority"], "⚪")
                task_lines.append(f"  {icon} {t['text']}")
            task_block = "📋 *Today's Tasks*\n" + "\n".join(task_lines)
        else:
            task_block = "📋 *No tasks today.* Add one with /addtask"

        carryover_note = (
            f"\n📦 _{carried} overdue task(s) carried over to today._" if carried > 0 else ""
        )

        quote = get_random_quote()

        text = (
            f"☀️ *Good morning, Bardi.*\n"
            f"📆 *{today}*\n\n"
            f"💥 _{quote}_\n\n"
            f"{lecture_block}\n"
            f"{study_block}\n"
            f"{task_block}"
            f"{carryover_note}"
        )
        await app.bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown")
    except Exception:
        logger.exception("job_morning_schedule failed")


# ---------------------------------------------------------------------------
# Job: Exam Countdown (08:00 daily)
# ---------------------------------------------------------------------------
async def job_exam_countdown(app: Application) -> None:
    try:
        upcoming = get_upcoming_exams()
        if not upcoming:
            return
        chat_id = _chat_id()
        lines = ["⚠️ *Exam Alert*\n"]
        for e in upcoming:
            days = e["days_left"]
            urgency = "🔴" if days <= 3 else "🟡" if days <= 7 else "🟢"
            lines.append(f"  {urgency} *{e['course']}* — {days} day(s) away ({e['date'].strftime('%d %b')})")
        lines.append("\nStop scrolling. Open your notes.")
        await app.bot.send_message(chat_id=chat_id, text="\n".join(lines), parse_mode="Markdown")
    except Exception:
        logger.exception("job_exam_countdown failed")


# ---------------------------------------------------------------------------
# Job: Lecture Reminder (30 min before each lecture)
# ---------------------------------------------------------------------------
def _make_lecture_reminder(course: str, start_time: str):
    async def job(app: Application) -> None:
        try:
            chat_id = _chat_id()
            await app.bot.send_message(
                chat_id=chat_id,
                text=(
                    f"🔔 *Lecture in 30 minutes*\n\n"
                    f"📚 {course} starts at {start_time}\n\n"
                    f"Pack your bag. Get there early."
                ),
                parse_mode="Markdown",
            )
        except Exception:
            logger.exception("lecture reminder job failed for %s", course)
    job.__name__ = f"reminder_{course.replace(' ', '_')}_{start_time}"
    return job


# ---------------------------------------------------------------------------
# Job: Evening Check-In Prompt (21:00 daily)
# ---------------------------------------------------------------------------
async def job_evening_checkin(app: Application) -> None:
    try:
        chat_id = _chat_id()
        streaks = await get_streaks(chat_id)
        study_streak = streaks["study_streak"]
        streak_note = (
            f"🔥 You're on a {study_streak}-day study streak. Don't break it."
            if study_streak > 1
            else "Start your streak tonight."
        )
        await app.bot.send_message(
            chat_id=chat_id,
            text=(
                "🌙 *Evening Check-In Time*\n\n"
                f"{streak_note}\n\n"
                "Type /checkin to log today's progress."
            ),
            parse_mode="Markdown",
        )
    except Exception:
        logger.exception("job_evening_checkin failed")


# ---------------------------------------------------------------------------
# Job: Weekly Reset (Sunday 22:00)
# ---------------------------------------------------------------------------
async def job_weekly_reset(app: Application) -> None:
    try:
        chat_id = _chat_id()
        today = datetime.now(TIMEZONE).date()
        start = (today - timedelta(days=6)).isoformat()
        summary = await get_weekly_task_summary(chat_id, start)
        streaks = await get_streaks(chat_id)

        text = (
            "📅 *Weekly Reset — Sunday Review*\n\n"
            f"✅ Tasks completed: {summary['completed']}\n"
            f"❌ Tasks missed: {summary['missed']}\n\n"
            f"*Streaks*\n"
            f"📚 Study: {streaks['study_streak']} 🔥\n"
            f"💻 LeetCode: {streaks['leetcode_streak']} 🔥\n"
            f"🤖 Robotics: {streaks['robotics_streak']} 🔥\n\n"
            "New week starts now. Use /addtask to plan this week's goals.\n"
            "_One week of consistency changes everything._"
        )
        await app.bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown")
    except Exception:
        logger.exception("job_weekly_reset failed")


# ---------------------------------------------------------------------------
# Register all jobs and start scheduler
# ---------------------------------------------------------------------------
def start_scheduler(application: Application) -> None:
    """Register all cron jobs and start the scheduler."""

    # Morning schedule
    scheduler.add_job(
        job_morning_schedule, "cron",
        hour=MORNING_SCHEDULE_HOUR, minute=MORNING_SCHEDULE_MINUTE,
        id="morning_schedule", args=[application],
    )

    # Exam countdown
    scheduler.add_job(
        job_exam_countdown, "cron",
        hour=EXAM_COUNTDOWN_HOUR, minute=EXAM_COUNTDOWN_MINUTE,
        id="exam_countdown", args=[application],
    )

    # Lecture reminders — one job per lecture slot
    for weekday, lectures in LECTURE_SCHEDULE.items():
        day_names = {0: "mon", 1: "tue", 2: "wed", 3: "thu", 4: "fri", 5: "sat", 6: "sun"}
        day_str = day_names[weekday]
        seen = {}  # track duplicate course+time combos
        for lec in lectures:
            r_hour, r_min = reminder_time(lec["start"])
            job_id = f"reminder_{lec['course'].replace(' ', '_')}_{lec['start']}_{day_str}"
            # Avoid duplicate job IDs for back-to-back same-course slots
            count = seen.get(job_id, 0)
            seen[job_id] = count + 1
            if count > 0:
                job_id = f"{job_id}_{count}"
            scheduler.add_job(
                _make_lecture_reminder(lec["course"], lec["start"]),
                "cron",
                day_of_week=day_str, hour=r_hour, minute=r_min,
                id=job_id, args=[application],
            )

    # Evening check-in
    scheduler.add_job(
        job_evening_checkin, "cron",
        hour=EVENING_CHECKIN_HOUR, minute=EVENING_CHECKIN_MINUTE,
        id="evening_checkin", args=[application],
    )

    # Weekly reset (Sunday)
    scheduler.add_job(
        job_weekly_reset, "cron",
        day_of_week="sun", hour=WEEKLY_RESET_HOUR, minute=WEEKLY_RESET_MINUTE,
        id="weekly_reset", args=[application],
    )

    scheduler.start()
    logger.info("Scheduler started with %d jobs.", len(scheduler.get_jobs()))
