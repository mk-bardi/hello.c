"""
ai_helper.py — Claude API wrapper for BardiOS.
Uses Anthropic AsyncAnthropic client; reads ANTHROPIC_API_KEY from environment automatically.
Model: claude-opus-4-6 with adaptive thinking for task breakdown.
"""

import logging

import anthropic

from bardi_bot.config import get_random_quote

logger = logging.getLogger(__name__)

_client = anthropic.AsyncAnthropic()

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
    """
    Use Claude Opus 4.6 with adaptive thinking to break a task into 3-5 numbered steps.
    Falls back to a generic message on error.
    """
    try:
        response = await _client.messages.create(
            model="claude-opus-4-6",
            max_tokens=1024,
            thinking={"type": "adaptive"},
            system=_BREAKDOWN_SYSTEM,
            messages=[
                {"role": "user", "content": f"Break this task into steps: {task_name}"},
            ],
        )
        # Extract the text block from the response (skip thinking blocks)
        for block in response.content:
            if block.type == "text":
                return block.text.strip()
        return "Could not generate breakdown. Try again."
    except Exception as e:
        logger.error("Claude breakdown_task failed: %s", e)
        return (
            "AI is unavailable right now. Here's a default breakdown:\n"
            "1. Open your notes — 5 min\n"
            "2. Review the last topic — 15 min\n"
            "3. Watch one related video — 20 min\n"
            "4. Solve 2–3 practice problems — 20 min\n"
            "5. Write a 3-line summary — 5 min"
        )


async def get_motivational_response(context_text: str) -> str:
    """
    Use Claude Opus 4.6 to generate a tailored motivational push based on check-in context.
    Falls back to a random quote on error.
    """
    try:
        response = await _client.messages.create(
            model="claude-opus-4-6",
            max_tokens=150,
            system=_MOTIVATION_SYSTEM,
            messages=[
                {"role": "user", "content": context_text},
            ],
        )
        for block in response.content:
            if block.type == "text":
                return block.text.strip()
        return get_random_quote()
    except Exception as e:
        logger.error("Claude motivation failed: %s", e)
        return get_random_quote()
