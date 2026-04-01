"""
ai_helper.py — Zero-cost AI for BardiOS.

No API key required. Uses smart keyword-based templates for task breakdown
and curated context-aware responses for motivation.

If ANTHROPIC_API_KEY is set in .env, Claude Opus 4.6 is used instead.
This means the bot works completely free out of the box, with optional
upgrade to real AI just by adding an API key later.
"""

import logging
import os
import re

from bardi_bot.config import get_random_quote

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Keyword → step templates for ADHD-friendly task breakdown
# ---------------------------------------------------------------------------
_TEMPLATES: list[tuple[list[str], list[str]]] = [
    # Study / revision / notes
    (
        ["study", "revise", "revision", "review", "notes", "lecture", "read", "chapter",
         "mcen", "enml", "control", "dynamics", "thermodynamics", "fluid", "mech", "engineering"],
        [
            "1. Open your notes and scan headings — 5 min",
            "2. Re-read the last topic you covered — 15 min",
            "3. Watch one short YouTube explanation — 15 min",
            "4. Solve 2–3 practice questions — 20 min",
            "5. Write a 5-point summary from memory — 5 min",
        ],
    ),
    # Exam prep / past questions
    (
        ["exam", "test", "past question", "past paper", "prepare", "preparation", "cram"],
        [
            "1. List every topic on the syllabus — 5 min",
            "2. Mark topics: know it / shaky / blank — 5 min",
            "3. Attack one 'shaky' topic (notes + examples) — 25 min",
            "4. Solve 3 past exam questions on that topic — 20 min",
            "5. Write key formulas on a single cheat sheet — 5 min",
        ],
    ),
    # Assignment / report / write-up
    (
        ["assignment", "report", "write", "writeup", "submit", "coursework", "project", "essay"],
        [
            "1. Re-read the question/brief in full — 5 min",
            "2. List every section you need to write — 5 min",
            "3. Write bullet-point content for each section — 20 min",
            "4. Expand bullets into full sentences — 20 min",
            "5. Proofread and format for submission — 10 min",
        ],
    ),
    # LeetCode / DSA / coding practice
    (
        ["leetcode", "dsa", "algorithm", "data structure", "coding", "problem", "array",
         "linked list", "tree", "graph", "dynamic programming", "dp", "binary search"],
        [
            "1. Read the problem statement twice without touching code — 3 min",
            "2. Write out the approach in plain English — 5 min",
            "3. Code a brute-force solution first — 15 min",
            "4. Test with 2 edge cases (empty input, max size) — 5 min",
            "5. Optimise the solution and note the time complexity — 10 min",
        ],
    ),
    # Python / programming / Udemy course
    (
        ["python", "udemy", "course", "lesson", "module", "program", "script", "function",
         "class", "debug", "error", "bug", "code"],
        [
            "1. Open the course / editor and review where you left off — 5 min",
            "2. Watch / read the next lesson without skipping — 20 min",
            "3. Type out the example code yourself (no copy-paste) — 10 min",
            "4. Modify the example to do something slightly different — 10 min",
            "5. Push your work to GitHub or save with a comment — 5 min",
        ],
    ),
    # ROS 2 / robotics
    (
        ["ros", "ros2", "robot", "robotics", "autonomous", "slam", "navigation", "sensor",
         "lidar", "camera", "urdf", "gazebo", "simulation", "stanford"],
        [
            "1. Open the ROS 2 docs / course and find today's topic — 5 min",
            "2. Read through the concept without running anything — 10 min",
            "3. Run the tutorial example and observe the output — 15 min",
            "4. Modify one parameter and observe what changes — 10 min",
            "5. Write 3 sentences explaining what you learned — 5 min",
        ],
    ),
    # Reading / research / paper
    (
        ["read", "paper", "article", "journal", "research", "textbook", "book"],
        [
            "1. Skim headings and abstract to get the structure — 5 min",
            "2. Read the introduction in full — 10 min",
            "3. Read one section at a time, highlight key points — 20 min",
            "4. Write a 5-bullet summary of the main ideas — 5 min",
            "5. Note one question it raised for follow-up — 2 min",
        ],
    ),
    # Lab / practical / experiment
    (
        ["lab", "practical", "experiment", "simulation", "matlab", "simulink", "circuit",
         "prototype", "build", "solder", "breadboard"],
        [
            "1. Read the lab sheet / objective in full — 5 min",
            "2. Gather all equipment / open the software — 5 min",
            "3. Complete the setup / circuit / simulation — 20 min",
            "4. Record your results and take screenshots — 10 min",
            "5. Write the observation and conclusion section — 10 min",
        ],
    ),
]

_DEFAULT_STEPS = [
    "1. Write down exactly what 'done' looks like for this task — 3 min",
    "2. Identify the single first physical action you can take — 2 min",
    "3. Do that first action without stopping — 25 min",
    "4. Review what you did and what's left — 5 min",
    "5. Schedule the next session immediately — 2 min",
]

# ---------------------------------------------------------------------------
# Motivation templates keyed by (study, leetcode, robotics) done count
# ---------------------------------------------------------------------------
_MOTIVATION_BY_SCORE: dict[int, list[str]] = {
    3: [
        "3 out of 3. That's a complete day. Build on it.",
        "Full house. Rare. Keep this standard.",
        "Study. Code. Robotics. All three. You're serious now.",
    ],
    2: [
        "2 out of 3. Solid. What stopped the third? Fix it tomorrow.",
        "Good day. One gap. Name it and close it next time.",
        "Two wins is better than zero. Do all three tomorrow.",
    ],
    1: [
        "One win is a start. Make it two tomorrow.",
        "You showed up for one thing. Good. Now add one more.",
        "Don't let one become the ceiling. Push for two.",
    ],
    0: [
        "Nothing logged. Tomorrow is the reset. Use it.",
        "Zero today. That means tomorrow has to count double.",
        "Rest is fine once. Twice is a habit. Don't let it be twice.",
    ],
}


def _match_template(task_name: str) -> list[str]:
    """Match task name against keyword templates, return best-fit steps."""
    lower = task_name.lower()
    for keywords, steps in _TEMPLATES:
        if any(kw in lower for kw in keywords):
            return steps
    return _DEFAULT_STEPS


def _build_breakdown(task_name: str) -> str:
    steps = _match_template(task_name)
    return "\n".join(steps)


def _build_motivation(context_text: str) -> str:
    """Pick a motivation line based on how many goals were completed."""
    match = re.search(r"(\d)/3 goals", context_text)
    score = int(match.group(1)) if match else 1
    import random
    options = _MOTIVATION_BY_SCORE.get(score, _MOTIVATION_BY_SCORE[1])
    return random.choice(options)


# ---------------------------------------------------------------------------
# Optional Claude API upgrade
# ---------------------------------------------------------------------------
_USE_CLAUDE = bool(os.getenv("ANTHROPIC_API_KEY"))

if _USE_CLAUDE:
    try:
        import anthropic as _anthropic
        _claude = _anthropic.AsyncAnthropic()
        logger.info("Claude API detected — using claude-opus-4-6 for AI features.")
    except ImportError:
        _USE_CLAUDE = False
        logger.warning("anthropic package not installed; falling back to built-in templates.")
else:
    logger.info("No ANTHROPIC_API_KEY set — using built-in templates (free mode).")

_BREAKDOWN_SYSTEM = (
    "You are an ADHD productivity coach for Muhammad Bardi, a mechatronics engineering student. "
    "When given a task, break it into exactly 3–5 numbered, concrete action steps with a realistic "
    "time estimate per step (e.g. '10 min'). Be brief, specific, and actionable. "
    "Do NOT add motivational fluff — just clear steps. "
    "Format each step as: '1. [Action] — [time estimate]'"
)

_MOTIVATION_SYSTEM = (
    "You are a strict but supportive productivity coach. "
    "Give a single short, sharp motivational push (1–2 sentences max) based on the user's check-in. "
    "Be direct. No filler words."
)


async def breakdown_task(task_name: str) -> str:
    """Break a task into steps. Uses Claude if API key is set, else smart templates."""
    if _USE_CLAUDE:
        try:
            response = await _claude.messages.create(
                model="claude-opus-4-6",
                max_tokens=1024,
                thinking={"type": "adaptive"},
                system=_BREAKDOWN_SYSTEM,
                messages=[{"role": "user", "content": f"Break this task into steps: {task_name}"}],
            )
            for block in response.content:
                if block.type == "text":
                    return block.text.strip()
        except Exception as e:
            logger.error("Claude breakdown_task failed: %s", e)

    return _build_breakdown(task_name)


async def get_motivational_response(context_text: str) -> str:
    """Return a motivational message. Uses Claude if API key is set, else curated lines."""
    if _USE_CLAUDE:
        try:
            response = await _claude.messages.create(
                model="claude-opus-4-6",
                max_tokens=150,
                system=_MOTIVATION_SYSTEM,
                messages=[{"role": "user", "content": context_text}],
            )
            for block in response.content:
                if block.type == "text":
                    return block.text.strip()
        except Exception as e:
            logger.error("Claude motivation failed: %s", e)

    return _build_motivation(context_text)
