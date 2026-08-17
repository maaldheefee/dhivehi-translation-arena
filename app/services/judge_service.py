"""Direct AI judging for pairwise translation comparisons."""

import json
from dataclasses import dataclass

from openrouter import OpenRouter

from app.config import get_config

JUDGE_MODEL = "google/gemini-3.7-flash"


@dataclass(frozen=True)
class JudgeResult:
    winner: str
    comments: str | None
    cost: float
    generation_id: str | None = None
    served_model: str | None = None
    provider_name: str | None = None
    service_tier: str | None = None


def judge_translations(source_text: str, translation_a: str, translation_b: str) -> JudgeResult:
    """Judge two translations and return the verdict plus OpenRouter's billed cost."""
    config = get_config()
    if not config.OPENROUTER_API_KEY:
        raise RuntimeError("OpenRouter API key is not configured")

    client = OpenRouter(
        api_key=config.OPENROUTER_API_KEY,
        http_referer=config.OPENROUTER_HTTP_REFERER,
        x_open_router_title=config.OPENROUTER_APP_TITLE,
        x_open_router_categories=config.OPENROUTER_APP_CATEGORIES,
    )
    response = client.chat.send(
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
        provider={"zdr": True} if config.OPENROUTER_ENFORCE_ZDR else None,
        timeout_ms=90_000,
    )
    if not response.choices or not response.choices[0].message.content:
        raise RuntimeError("Judge returned no result")

    payload = json.loads(response.choices[0].message.content)
    winner = payload.get("winner")
    if winner not in {"a", "b", "tie"}:
        raise RuntimeError("Judge returned an invalid winner")

    response_data = response.model_dump()
    usage_data = response_data.get("usage") or {}
    cost = float(usage_data.get("cost") or 0.0)
    comments = payload.get("comments") or None
    attempts = ((response_data.get("openrouter_metadata") or {}).get("attempts") or [])
    provider_name = attempts[-1].get("provider") if attempts else None
    return JudgeResult(
        winner=winner, comments=comments, cost=cost, generation_id=response_data.get("id"),
        served_model=response_data.get("model"), provider_name=provider_name,
        service_tier=response_data.get("service_tier"),
    )
