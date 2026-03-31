"""
ai_helper.py — Thin async wrapper around OpenAI for Bardi Assistant.
Uses AsyncOpenAI; reads OPENAI_API_KEY from environment automatically.
"""

import logging

from openai import AsyncOpenAI

from bardi_bot.config import get_random_quote

logger = logging.getLogger(__name__)

_client = AsyncOpenAI()

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
    Use GPT-4o-mini to break a task into 3-5 numbered steps with time estimates.
    Falls back to a generic message on error.
    """
    try:
        response = await _client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": _BREAKDOWN_SYSTEM},
                {"role": "user", "content": f"Break this task into steps: {task_name}"},
            ],
            max_tokens=300,
            temperature=0.3,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error("OpenAI breakdown_task failed: %s", e)
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
    Generate a tailored motivational push based on check-in context.
    Falls back to a random quote on error.
    """
    try:
        response = await _client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": _MOTIVATION_SYSTEM},
                {"role": "user", "content": context_text},
            ],
            max_tokens=80,
            temperature=0.7,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error("OpenAI motivation failed: %s", e)
        return get_random_quote()
