import json
from types import SimpleNamespace

from app.services import judge_service


def test_judge_uses_requested_model_and_openrouter_reported_cost(monkeypatch):
    captured = {}

    class Chat:
        def send(self, **kwargs):
            captured.update(kwargs)
            message = SimpleNamespace(content=json.dumps({"winner": "a", "comments": None}))
            return SimpleNamespace(
                choices=[SimpleNamespace(message=message)],
                model_dump=lambda: {"usage": {"cost": 0.0042}, "id": "gen-1", "model": "served"},
            )

    fake_client = SimpleNamespace(chat=Chat())
    monkeypatch.setattr(judge_service, "OpenRouter", lambda **_kwargs: fake_client)
    monkeypatch.setattr(
        judge_service,
        "get_config",
        lambda: SimpleNamespace(
            OPENROUTER_API_KEY="key",
            OPENROUTER_HTTP_REFERER=None,
            OPENROUTER_APP_TITLE="Arena",
            OPENROUTER_APP_CATEGORIES=None,
            OPENROUTER_ENFORCE_ZDR=False,
        ),
    )

    result = judge_service.judge_translations("source", "A", "B")

    assert captured["model"] == "google/gemini-3.7-flash"
    assert captured["response_format"]["type"] == "json_schema"
    assert result == judge_service.JudgeResult(winner="a", comments=None, cost=0.0042, generation_id="gen-1", served_model="served")
