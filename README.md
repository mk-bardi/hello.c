# Bardi Assistant — Telegram Bot

A personal AI productivity system for Muhammad Mukhtar Bardi — mechatronics engineering student with ADHD. The bot acts as a strict executive assistant: enforcing structure, sending reminders, breaking tasks into steps, and tracking academic + robotics + personal development progress.

---

## Features

| Feature | Command(s) | Description |
|---------|-----------|-------------|
| Daily Schedule | Auto 6 AM | Morning message with lectures, study blocks & tasks |
| Lecture Reminders | Auto | 30 min before each lecture |
| Exam Countdown | Auto 8 AM | Daily alert when exam is ≤ 14 days away |
| Task Manager | `/addtask` `/today` `/done` `/overdue` | Priority-tagged tasks with auto carry-over |
| Study Mode | `/focus` `/stopfocus` | 50-min Pomodoro + 10-min break timer |
| AI Task Breakdown | `/breakdown` | GPT-4o-mini decomposes any task into 3–5 steps |
| Evening Check-In | `/checkin` or auto 9 PM | Log study/LeetCode/robotics + streak tracking |
| Streaks | `/streak` | Study, LeetCode, robotics streaks |
| Weekly Review | `/weekly` or auto Sunday 10 PM | Summary + streak report |
| Motivation | `/motivate` | Random sharp motivational quote |

---

## Tech Stack

- **Python 3.11+**
- **python-telegram-bot 21.5** — async Telegram client
- **OpenAI API** — GPT-4o-mini for task breakdown + motivational responses
- **aiosqlite** — async SQLite database
- **APScheduler** — cron-style scheduled jobs
- **python-dotenv** — environment variable management

---

## Setup Guide

### 1. Prerequisites

- Python 3.11+
- A Telegram bot token from [@BotFather](https://t.me/BotFather)
- An OpenAI API key
- Your Telegram Chat ID (get it from [@userinfobot](https://t.me/userinfobot))

### 2. Clone & Install

```bash
git clone <your-repo-url>
cd hello.c
pip install -r requirements.txt
```

### 3. Configure Environment

```bash
cp .env.example .env
```

Edit `.env`:
```
BOT_TOKEN=your_bot_token_here
OPENAI_API_KEY=your_openai_key_here
CHAT_ID=your_telegram_chat_id_here
DATABASE_PATH=bardi.db
```

### 4. Run Locally

```bash
python bardi_bot/bot.py
```

The bot starts polling. Send `/start` in Telegram to verify it's working.

---

## Bot Commands

```
/start       — Welcome message + full command list
/help        — Show all commands
/today       — Today's lectures, study blocks & tasks
/addtask     — Add a new task (guided: text → priority → due date)
/done        — Mark a task complete
/overdue     — View overdue tasks
/focus       — Start 50-min Pomodoro session
/stopfocus   — Cancel active focus session
/breakdown   — AI task breakdown (GPT-4o-mini)
/checkin     — Evening accountability check-in
/streak      — View study/LeetCode/robotics streaks
/motivate    — Get a motivational push
/weekly      — This week's summary
```

---

## Deployment on Render.com

### Service Type: Background Worker

> Use **Background Worker**, not Web Service. No HTTP server required.

### Steps

1. Push this repository to GitHub
2. Go to [Render.com](https://render.com) → New → **Background Worker**
3. Connect your GitHub repository
4. Configure:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python bardi_bot/bot.py`
5. Add Environment Variables in the Render dashboard:
   ```
   BOT_TOKEN=...
   OPENAI_API_KEY=...
   CHAT_ID=...
   DATABASE_PATH=/data/bardi.db
   ```
6. Add a **Persistent Disk** (Render paid feature) mounted at `/data` to preserve the SQLite database across restarts
   - **Free alternative:** Use `DATABASE_PATH=/tmp/bardi.db` (data resets on restart — acceptable for a personal bot)

### Alternative: Railway.app

1. New Project → Deploy from GitHub
2. Add environment variables
3. Set Start Command: `python bardi_bot/bot.py`

### Alternative: VPS (Ubuntu)

```bash
# Install deps
pip install -r requirements.txt

# Run with systemd or screen
screen -S bardi
python bardi_bot/bot.py
# Ctrl+A, D to detach
```

---

## Sample Conversation

```
You: /start
Bot: 👋 Bardi Assistant Online. I enforce structure...

You: /addtask
Bot: 📝 New Task — What's the task?
You: Finish Control Engineering assignment
Bot: Priority? [🔴 High] [🟡 Medium] [🟢 Low]
You: [clicks 🔴 High]
Bot: Due date? (today/tomorrow/YYYY-MM-DD/none)
You: tomorrow
Bot: ✅ Task added — 🔴 Finish Control Engineering assignment — Due: 2026-04-01

You: /breakdown
Bot: 🧠 Task Breakdown — What task?
You: Study Control Engineering
Bot: 📋 Study Control Engineering

1. Open lecture notes — 5 min
2. Review last class topic (stability analysis) — 15 min
3. Watch 1 related video (Routh-Hurwitz) — 20 min
4. Solve 3 practice problems — 25 min
5. Write a 3-line summary of key takeaways — 5 min

Ready to start? Type /focus

You: /focus
Bot: 🔒 Focus mode ON. No distractions. Start now. I'll check back in 50 minutes.
... 50 minutes later ...
Bot: ⏸ 50 minutes done. Take a 10-minute break. Walk. Breathe. Hydrate.
... 10 minutes later ...
Bot: ▶️ Break over. Back to work. Type /focus to start another session.

[9:00 PM — automatic message]
Bot: 🌙 Evening Check-In Time. You're on a 3-day study streak. Don't break it.
     Type /checkin to log today's progress.

You: /checkin
Bot: Did you study today? [✅ Yes] [❌ No]
You: [✅ Yes]
Bot: LeetCode today? [✅ Yes] [❌ No]
You: [✅ Yes]
Bot: Robotics / ROS 2 today? [✅ Yes] [❌ No]
You: [❌ No]
Bot: Any notes? (or 'skip')
You: Studied Routh-Hurwitz for 2 hours. LeetCode: binary search problems.
Bot: 📊 Tonight's Log
     📚 Study: ✅ — 🔥 4 day streak
     💻 LeetCode: ✅ — 🔥 2 day streak
     🤖 Robotics: ❌ — Streak reset
     📝 Notes: Studied Routh-Hurwitz...
     💥 4 days in a row on study. One more and you own the week.
```

---

## Project Structure

```
hello.c/
├── bardi_bot/
│   ├── bot.py              # Entry point
│   ├── config.py           # Schedules, exams, quotes, constants
│   ├── database.py         # Async SQLite CRUD
│   ├── scheduler.py        # APScheduler cron jobs
│   ├── ai_helper.py        # OpenAI integration
│   └── handlers/
│       ├── __init__.py
│       ├── commands.py     # /start /help /today /streak /motivate /weekly
│       ├── tasks.py        # /addtask /done /overdue
│       ├── focus.py        # /focus /stopfocus
│       ├── breakdown.py    # /breakdown
│       └── accountability.py  # /checkin
├── requirements.txt
├── .env.example
├── Procfile
└── README.md
```

---

## Scheduled Jobs (WAT — Africa/Lagos, UTC+1)

| Job | Time | Description |
|-----|------|-------------|
| Morning Schedule | 06:00 daily | Lectures + study blocks + tasks + motivational quote |
| Exam Countdown | 08:00 daily | Alert for exams ≤ 14 days away |
| Lecture Reminders | 30 min before each | Per-lecture cron jobs |
| Evening Check-In | 21:00 daily | Prompt to log the day |
| Weekly Reset | Sunday 22:00 | Week summary + streak report |
