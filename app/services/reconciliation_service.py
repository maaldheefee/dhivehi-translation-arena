"""Audit local OpenRouter costs against generation metadata."""

from dataclasses import dataclass

from openrouter import OpenRouter

from app.config import get_config
from app.database import db_session
from app.models import Translation


@dataclass(frozen=True)
class ReconciliationSummary:
    checked: int
    mismatches: int
    missing: int


def reconcile_openrouter_generations() -> ReconciliationSummary:
    """Compare billed translation costs with OpenRouter's immutable generation record."""
    config = get_config()
    if not config.OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY is required for reconciliation")
    client = OpenRouter(api_key=config.OPENROUTER_API_KEY)
    checked = mismatches = missing = 0
    for translation in db_session.query(Translation).filter(Translation.generation_id.is_not(None)):
        checked += 1
        try:
            generation = client.generations.get_generation(id=str(translation.generation_id)).model_dump()["data"]
        except Exception:  # noqa: BLE001 - audit continues when a remote record is unavailable
            missing += 1
            continue
        billed_cost = float(generation.get("total_cost") or generation.get("usage") or 0.0)
        if abs(translation.cost - billed_cost) > 0.0000001:
            mismatches += 1
    return ReconciliationSummary(checked=checked, mismatches=mismatches, missing=missing)
