"""
config.py — All static configuration for Bardi Assistant.
No business logic, no I/O. Pure constants and helper functions.
"""

import random
from datetime import date, datetime

import pytz

# ---------------------------------------------------------------------------
# Timezone
# ---------------------------------------------------------------------------
TIMEZONE = pytz.timezone("Africa/Lagos")  # WAT, UTC+1

# ---------------------------------------------------------------------------
# Pomodoro
# ---------------------------------------------------------------------------
POMODORO_WORK_MIN = 50
POMODORO_BREAK_MIN = 10
POMODORO_WORK_SEC = POMODORO_WORK_MIN * 60
POMODORO_BREAK_SEC = POMODORO_BREAK_MIN * 60

# ---------------------------------------------------------------------------
# Scheduler timing
# ---------------------------------------------------------------------------
MORNING_SCHEDULE_HOUR = 6
MORNING_SCHEDULE_MINUTE = 0
EVENING_CHECKIN_HOUR = 21
EVENING_CHECKIN_MINUTE = 0
EXAM_COUNTDOWN_HOUR = 8
EXAM_COUNTDOWN_MINUTE = 0
WEEKLY_RESET_HOUR = 22
WEEKLY_RESET_MINUTE = 0
LECTURE_REMINDER_MIN_BEFORE = 30  # minutes before lecture start

# ---------------------------------------------------------------------------
# Exam alert threshold
# ---------------------------------------------------------------------------
EXAM_COUNTDOWN_THRESHOLD_DAYS = 14

# ---------------------------------------------------------------------------
# Lecture Schedule
# Weekday index: 0=Mon, 1=Tue, 2=Wed, 3=Thu, 4=Fri, 5=Sat, 6=Sun
# ---------------------------------------------------------------------------
LECTURE_SCHEDULE: dict[int, list[dict]] = {
    0: [  # Monday
        {"course": "MCEN 511", "start": "09:00", "end": "11:00"},
        {"course": "MCEN 503", "start": "14:00", "end": "16:00"},
    ],
    1: [  # Tuesday
        {"course": "MCEN 508", "start": "11:00", "end": "13:00"},
        {"course": "MCEN 508", "start": "14:00", "end": "16:00"},
    ],
    2: [  # Wednesday
        {"course": "MCEN 511", "start": "09:00", "end": "11:00"},
        {"course": "MCEN 509", "start": "11:00", "end": "13:00"},
    ],
    4: [  # Friday
        {"course": "ENML 501", "start": "08:00", "end": "09:00"},
    ],
}

# ---------------------------------------------------------------------------
# Exam Schedule
# ---------------------------------------------------------------------------
EXAM_SCHEDULE: list[dict] = [
    {"course": "MCEN 521", "date": date(2026, 4, 13)},
    {"course": "MCEN 511", "date": date(2026, 4, 16)},
    {"course": "MCEN 501", "date": date(2026, 4, 22)},
    {"course": "MCEN 503", "date": date(2026, 4, 27)},
    {"course": "ENML 501", "date": date(2026, 4, 30)},
    {"course": "MCEN 509", "date": date(2026, 5, 4)},
    {"course": "MCEN 508", "date": date(2026, 5, 7)},
]

# ---------------------------------------------------------------------------
# Motivational Quotes
# ---------------------------------------------------------------------------
MOTIVATIONAL_QUOTES: list[str] = [
    "You're not tired. You're unfocused.",
    "Do 10 minutes. That's enough to win today.",
    "Discipline is choosing what you want most over what you want now.",
    "The best time to start was yesterday. The second best time is now.",
    "Stop waiting to feel ready. You never will. Start anyway.",
    "Your future self is watching. Don't let them down.",
    "One session. One task. One win. Build from there.",
    "Momentum doesn't find you. You build it.",
    "Robotics engineers are made in the hours others waste.",
    "You don't need motivation. You need a decision.",
    "Every great engineer was once a student who refused to quit.",
    "Hard now, easier later. That's the deal.",
    "Confusion is the beginning of understanding. Push through it.",
    "Your competition is consistent. Are you?",
    "Small steps every day beat giant leaps once a month.",
    "Focus is a muscle. Train it daily.",
    "You chose mechatronics. That wasn't the easy path. Keep going.",
    "LeetCode today means opportunities tomorrow.",
    "ROS 2 doesn't care about your mood. Neither should you.",
    "The algorithm won't debug itself. Get back to work.",
    "Excellence is a habit, not a talent.",
    "Five years from now, today's effort will matter.",
]

# ---------------------------------------------------------------------------
# Study block templates by day type
# ---------------------------------------------------------------------------
def build_study_schedule(lectures: list[dict]) -> str:
    """Generate a study block schedule around the day's lectures."""
    if not lectures:
        # No lectures — full study day
        return (
            "📚 *Study Blocks (No Lectures Today)*\n"
            "  08:00–08:50 — Deep Work Block 1\n"
            "  08:50–09:00 — Break\n"
            "  09:00–09:50 — Deep Work Block 2\n"
            "  09:50–10:00 — Break\n"
            "  11:00–11:50 — LeetCode Practice\n"
            "  11:50–12:00 — Break\n"
            "  14:00–14:50 — Robotics / ROS 2 Study\n"
            "  14:50–15:00 — Break\n"
            "  16:00–16:50 — Python / Udemy Course\n"
            "  20:00–20:50 — Exam Revision\n"
        )
    else:
        return (
            "📚 *Study Blocks*\n"
            "  07:00–07:50 — Morning Revision\n"
            "  07:50–08:00 — Break\n"
            "  12:00–12:50 — LeetCode Practice\n"
            "  12:50–13:00 — Break\n"
            "  17:00–17:50 — Robotics / ROS 2 Study\n"
            "  17:50–18:00 — Break\n"
            "  19:00–19:50 — Python / Udemy Course\n"
            "  19:50–20:00 — Break\n"
            "  20:00–20:50 — Exam Revision\n"
        )


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------
def get_today_lectures() -> list[dict]:
    """Return lecture list for today's weekday (WAT), or [] if no class."""
    today_weekday = datetime.now(TIMEZONE).weekday()
    return LECTURE_SCHEDULE.get(today_weekday, [])


def get_lectures_for_weekday(weekday: int) -> list[dict]:
    """Return lecture list for a given weekday index."""
    return LECTURE_SCHEDULE.get(weekday, [])


def get_upcoming_exams(within_days: int = EXAM_COUNTDOWN_THRESHOLD_DAYS) -> list[dict]:
    """Return exams whose date is between today and today+within_days (inclusive)."""
    today = datetime.now(TIMEZONE).date()
    result = []
    for exam in EXAM_SCHEDULE:
        days_left = (exam["date"] - today).days
        if 0 <= days_left <= within_days:
            result.append({**exam, "days_left": days_left})
    return result


def get_random_quote() -> str:
    """Return a random motivational quote."""
    return random.choice(MOTIVATIONAL_QUOTES)


def format_lecture_block(lectures: list[dict]) -> str:
    """Format today's lectures as a readable string."""
    if not lectures:
        return "📅 *No lectures today.* Full study day — no excuses.\n"
    lines = ["📅 *Today's Lectures*"]
    for lec in lectures:
        lines.append(f"  • {lec['course']}: {lec['start']} – {lec['end']}")
    return "\n".join(lines) + "\n"


def parse_time_to_hhmm(time_str: str) -> tuple[int, int]:
    """Convert 'HH:MM' string to (hour, minute) tuple."""
    parts = time_str.split(":")
    return int(parts[0]), int(parts[1])


def reminder_time(time_str: str, minutes_before: int = LECTURE_REMINDER_MIN_BEFORE) -> tuple[int, int]:
    """Return (hour, minute) for a reminder N minutes before a given HH:MM time."""
    h, m = parse_time_to_hhmm(time_str)
    total_minutes = h * 60 + m - minutes_before
    return total_minutes // 60, total_minutes % 60
