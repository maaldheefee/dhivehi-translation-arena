import json
from types import SimpleNamespace

from app.services import judge_service


def test_judge_uses_requested_model_and_openrouter_reported_cost(monkeypatch):
    captured = {}

    class Completions:
        def create(self, **kwargs):
            captured.update(kwargs)
            usage = SimpleNamespace(model_dump=lambda: {"cost": 0.0042})
            message = SimpleNamespace(content=json.dumps({"winner": "a", "comments": None}))
            return SimpleNamespace(choices=[SimpleNamespace(message=message)], usage=usage)

    fake_client = SimpleNamespace(chat=SimpleNamespace(completions=Completions()))
    monkeypatch.setattr(judge_service, "OpenAI", lambda **_kwargs: fake_client)
    monkeypatch.setattr(
        judge_service,
        "get_config",
        lambda: SimpleNamespace(
            OPENROUTER_API_KEY="key",
            OPENROUTER_BASE_URL="https://openrouter.example/api/v1",
        ),
    )

    result = judge_service.judge_translations("source", "A", "B")

    assert captured["model"] == "google/gemini-3.7-flash"
    assert captured["response_format"]["type"] == "json_schema"
    assert result == judge_service.JudgeResult(winner="a", comments=None, cost=0.0042)
