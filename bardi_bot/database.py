"""
database.py — All async SQLite I/O for Bardi Assistant.
Uses aiosqlite with per-call context managers (no persistent connection).
All datetimes are stored as ISO strings using Africa/Lagos timezone.
"""

import os
from datetime import datetime, timedelta

import aiosqlite

from bardi_bot.config import TIMEZONE

DB_PATH = os.getenv("DATABASE_PATH", "bardi.db")

# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------
_SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id      INTEGER NOT NULL,
    text         TEXT    NOT NULL,
    priority     TEXT    NOT NULL DEFAULT 'Medium',
    due_date     TEXT,
    status       TEXT    NOT NULL DEFAULT 'pending',
    created_at   TEXT    NOT NULL,
    completed_at TEXT
);

CREATE TABLE IF NOT EXISTS daily_logs (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id       INTEGER NOT NULL,
    date          TEXT    NOT NULL,
    study_done    INTEGER NOT NULL DEFAULT 0,
    leetcode_done INTEGER NOT NULL DEFAULT 0,
    robotics_done INTEGER NOT NULL DEFAULT 0,
    notes         TEXT,
    UNIQUE(user_id, date)
);

CREATE TABLE IF NOT EXISTS streaks (
    user_id          INTEGER PRIMARY KEY,
    study_streak     INTEGER NOT NULL DEFAULT 0,
    leetcode_streak  INTEGER NOT NULL DEFAULT 0,
    robotics_streak  INTEGER NOT NULL DEFAULT 0,
    last_updated     TEXT    NOT NULL
);
"""


async def init_db() -> None:
    """Create all tables if they don't exist. Call once at bot startup."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(_SCHEMA)
        await db.commit()


def _now_str() -> str:
    return datetime.now(TIMEZONE).isoformat()


def _today_str() -> str:
    return datetime.now(TIMEZONE).date().isoformat()


def _row_to_dict(row: aiosqlite.Row) -> dict:
    return dict(row)


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------
async def add_task(user_id: int, text: str, priority: str, due_date: str | None) -> int:
    """Insert a new task and return its id."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO tasks (user_id, text, priority, due_date, status, created_at) "
            "VALUES (?, ?, ?, ?, 'pending', ?)",
            (user_id, text, priority, due_date, _now_str()),
        )
        await db.commit()
        return cursor.lastrowid


async def get_today_tasks(user_id: int) -> list[dict]:
    """Tasks with status='pending' due today or with no due date."""
    today = _today_str()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM tasks WHERE user_id=? AND status='pending' "
            "AND (due_date=? OR due_date IS NULL) ORDER BY "
            "CASE priority WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 ELSE 3 END, created_at",
            (user_id, today),
        ) as cur:
            rows = await cur.fetchall()
    return [_row_to_dict(r) for r in rows]


async def get_all_pending_tasks(user_id: int) -> list[dict]:
    """All pending tasks regardless of due date."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM tasks WHERE user_id=? AND status='pending' ORDER BY "
            "CASE priority WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 ELSE 3 END, due_date, created_at",
            (user_id,),
        ) as cur:
            rows = await cur.fetchall()
    return [_row_to_dict(r) for r in rows]


async def get_overdue_tasks(user_id: int) -> list[dict]:
    """Tasks with status='pending' and due_date strictly before today."""
    today = _today_str()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM tasks WHERE user_id=? AND status='pending' "
            "AND due_date IS NOT NULL AND due_date < ? ORDER BY due_date",
            (user_id, today),
        ) as cur:
            rows = await cur.fetchall()
    return [_row_to_dict(r) for r in rows]


async def mark_task_done(task_id: int, user_id: int) -> bool:
    """Set task status to 'done'. Returns False if task not found or not owned."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "UPDATE tasks SET status='done', completed_at=? "
            "WHERE id=? AND user_id=? AND status='pending'",
            (_now_str(), task_id, user_id),
        )
        await db.commit()
        return cursor.rowcount > 0


async def carry_over_overdue(user_id: int) -> int:
    """Move all overdue pending tasks to today's due date. Returns count updated."""
    today = _today_str()
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "UPDATE tasks SET due_date=? WHERE user_id=? AND status='pending' "
            "AND due_date IS NOT NULL AND due_date < ?",
            (today, user_id, today),
        )
        await db.commit()
        return cursor.rowcount


async def delete_task(task_id: int, user_id: int) -> bool:
    """Hard-delete a task. Returns False if not found/owned."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "DELETE FROM tasks WHERE id=? AND user_id=?",
            (task_id, user_id),
        )
        await db.commit()
        return cursor.rowcount > 0


# ---------------------------------------------------------------------------
# Daily Logs
# ---------------------------------------------------------------------------
async def upsert_daily_log(
    user_id: int,
    date_str: str,
    study_done: bool,
    leetcode_done: bool,
    robotics_done: bool,
    notes: str | None,
) -> None:
    """Insert or replace a daily log entry."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO daily_logs (user_id, date, study_done, leetcode_done, robotics_done, notes) "
            "VALUES (?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(user_id, date) DO UPDATE SET "
            "study_done=excluded.study_done, "
            "leetcode_done=excluded.leetcode_done, "
            "robotics_done=excluded.robotics_done, "
            "notes=excluded.notes",
            (user_id, date_str, int(study_done), int(leetcode_done), int(robotics_done), notes),
        )
        await db.commit()


async def get_daily_log(user_id: int, date_str: str) -> dict | None:
    """Fetch a single day's log or None."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM daily_logs WHERE user_id=? AND date=?",
            (user_id, date_str),
        ) as cur:
            row = await cur.fetchone()
    return _row_to_dict(row) if row else None


async def get_weekly_logs(user_id: int, start_date: str, end_date: str) -> list[dict]:
    """Logs in [start_date, end_date] inclusive."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM daily_logs WHERE user_id=? AND date>=? AND date<=? ORDER BY date",
            (user_id, start_date, end_date),
        ) as cur:
            rows = await cur.fetchall()
    return [_row_to_dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Streaks
# ---------------------------------------------------------------------------
async def get_streaks(user_id: int) -> dict:
    """Return streak row or zeroed defaults."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM streaks WHERE user_id=?", (user_id,)
        ) as cur:
            row = await cur.fetchone()
    if row:
        return _row_to_dict(row)
    return {
        "user_id": user_id,
        "study_streak": 0,
        "leetcode_streak": 0,
        "robotics_streak": 0,
        "last_updated": _today_str(),
    }


async def update_streaks(user_id: int, study: bool, leetcode: bool, robotics: bool) -> dict:
    """
    Increment or reset each streak based on today's check-in values.
    Returns the updated streak dict.
    """
    today = _today_str()
    yesterday = (datetime.now(TIMEZONE).date() - timedelta(days=1)).isoformat()

    current = await get_streaks(user_id)
    yesterday_log = await get_daily_log(user_id, yesterday)

    def calc_streak(current_val: int, last_updated: str, today_done: bool, yesterday_done: bool) -> int:
        if not today_done:
            return 0
        # Today is True — increment if yesterday was also True OR streak just starting
        if yesterday_done or current_val == 0:
            return current_val + 1
        # Yesterday was missed but today is True — reset to 1
        return 1

    y_study = bool(yesterday_log and yesterday_log["study_done"]) if yesterday_log else False
    y_leet = bool(yesterday_log and yesterday_log["leetcode_done"]) if yesterday_log else False
    y_robot = bool(yesterday_log and yesterday_log["robotics_done"]) if yesterday_log else False

    new_study = calc_streak(current["study_streak"], current["last_updated"], study, y_study)
    new_leet = calc_streak(current["leetcode_streak"], current["last_updated"], leetcode, y_leet)
    new_robot = calc_streak(current["robotics_streak"], current["last_updated"], robotics, y_robot)

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO streaks (user_id, study_streak, leetcode_streak, robotics_streak, last_updated) "
            "VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET "
            "study_streak=excluded.study_streak, "
            "leetcode_streak=excluded.leetcode_streak, "
            "robotics_streak=excluded.robotics_streak, "
            "last_updated=excluded.last_updated",
            (user_id, new_study, new_leet, new_robot, today),
        )
        await db.commit()

    return {
        "user_id": user_id,
        "study_streak": new_study,
        "leetcode_streak": new_leet,
        "robotics_streak": new_robot,
        "last_updated": today,
    }


# ---------------------------------------------------------------------------
# Weekly summary
# ---------------------------------------------------------------------------
async def get_weekly_task_summary(user_id: int, start_date: str) -> dict:
    """Return {completed: int, missed: int} for tasks created in the past 7 days."""
    end_date = _today_str()
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM tasks WHERE user_id=? AND status='done' "
            "AND DATE(created_at)>=? AND DATE(created_at)<=?",
            (user_id, start_date, end_date),
        ) as cur:
            completed = (await cur.fetchone())[0]
        async with db.execute(
            "SELECT COUNT(*) FROM tasks WHERE user_id=? AND status='pending' "
            "AND due_date IS NOT NULL AND due_date>=? AND due_date<=?",
            (user_id, start_date, end_date),
        ) as cur:
            missed = (await cur.fetchone())[0]
    return {"completed": completed, "missed": missed}
