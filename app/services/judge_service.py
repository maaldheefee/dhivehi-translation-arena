"""Direct AI judging for pairwise translation comparisons."""

import json
from dataclasses import dataclass

from openai import OpenAI

from app.config import get_config

JUDGE_MODEL = "google/gemini-3.7-flash"


@dataclass(frozen=True)
class JudgeResult:
    winner: str
    comments: str | None
    cost: float


def judge_translations(source_text: str, translation_a: str, translation_b: str) -> JudgeResult:
    """Judge two translations and return the verdict plus OpenRouter's billed cost."""
    config = get_config()
    if not config.OPENROUTER_API_KEY:
        raise RuntimeError("OpenRouter API key is not configured")

    client = OpenAI(base_url=config.OPENROUTER_BASE_URL, api_key=config.OPENROUTER_API_KEY)
    response = client.chat.completions.create(
        model=JUDGE_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an expert, impartial judge of Dhivehi translations. Compare accuracy, fluency, "
                    "completeness, style, and cultural appropriateness. Return only the requested JSON."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Source text (Arabic):\n{source_text}\n\n"
                    f"Translation A:\n{translation_a}\n\nTranslation B:\n{translation_b}"
                ),
            },
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "translation_judgment",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "winner": {"type": "string", "enum": ["a", "b", "tie"]},
                        "comments": {"type": ["string", "null"]},
                    },
                    "required": ["winner", "comments"],
                    "additionalProperties": False,
                },
            },
        },
        temperature=1.0,
        timeout=90.0,
    )
    if not response.choices or not response.choices[0].message.content:
        raise RuntimeError("Judge returned no result")

    payload = json.loads(response.choices[0].message.content)
    winner = payload.get("winner")
    if winner not in {"a", "b", "tie"}:
        raise RuntimeError("Judge returned an invalid winner")

    usage = response.usage
    usage_data = usage.model_dump() if usage else {}
    cost = float(usage_data.get("cost") or 0.0)
    comments = payload.get("comments") or None
    return JudgeResult(winner=winner, comments=comments, cost=cost)
