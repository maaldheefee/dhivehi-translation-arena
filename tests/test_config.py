from concurrent.futures import ThreadPoolExecutor

import pytest

from app import config as config_module
from app.config import _load_models_from_yaml, _ModelsReloader


def _model_yaml(display_name: str) -> str:
    return f"""
test-model:
  name: provider/test-model
  display_name: {display_name}
  type: openrouter
  input_cost_per_mtok: 0.5
  output_cost_per_mtok: 2.0
  is_active: true
"""


def test_models_reloader_returns_same_snapshot_when_file_is_unchanged(tmp_path):
    yaml_file = tmp_path / "models.yaml"
    yaml_file.write_text(_model_yaml("Original"), encoding="utf-8")
    initial = _load_models_from_yaml(yaml_file)
    reloader = _ModelsReloader(yaml_file, initial)

    assert reloader.get() is initial


def test_models_reloader_loads_valid_file_changes(tmp_path):
    yaml_file = tmp_path / "models.yaml"
    yaml_file.write_text(_model_yaml("Original"), encoding="utf-8")
    reloader = _ModelsReloader(yaml_file, _load_models_from_yaml(yaml_file))

    yaml_file.write_text(_model_yaml("Updated model"), encoding="utf-8")

    assert reloader.get()["test-model"]["display_name"] == "Updated model"


def test_get_config_exposes_reloaded_models(tmp_path, monkeypatch):
    yaml_file = tmp_path / "models.yaml"
    yaml_file.write_text(_model_yaml("Original"), encoding="utf-8")
    reloader = _ModelsReloader(yaml_file, _load_models_from_yaml(yaml_file))
    monkeypatch.setattr(config_module, "_models_reloader", reloader)
    monkeypatch.setattr(config_module, "_config_instance", None)

    config = config_module.get_config("testing")
    yaml_file.write_text(_model_yaml("Updated through get_config"), encoding="utf-8")
    reloaded_config = config_module.get_config("testing")

    assert reloaded_config is config
    assert reloaded_config.MODELS["test-model"]["display_name"] == "Updated through get_config"


def test_models_reloader_keeps_last_valid_snapshot_and_recovers(tmp_path, caplog):
    yaml_file = tmp_path / "models.yaml"
    yaml_file.write_text(_model_yaml("Original"), encoding="utf-8")
    initial = _load_models_from_yaml(yaml_file)
    reloader = _ModelsReloader(yaml_file, initial)

    yaml_file.write_text("incomplete: [", encoding="utf-8")

    assert reloader.get() is initial
    assert "continuing with the last valid model configuration" in caplog.text

    yaml_file.write_text(_model_yaml("Recovered model"), encoding="utf-8")

    assert reloader.get()["test-model"]["display_name"] == "Recovered model"


def test_models_reloader_only_reloads_once_for_concurrent_readers(tmp_path, monkeypatch):
    yaml_file = tmp_path / "models.yaml"
    yaml_file.write_text(_model_yaml("Original"), encoding="utf-8")
    reloader = _ModelsReloader(yaml_file, _load_models_from_yaml(yaml_file))
    yaml_file.write_text(_model_yaml("Updated concurrently"), encoding="utf-8")
    original_loader = config_module._load_models_from_yaml
    load_count = 0

    def counting_loader(path):
        nonlocal load_count
        load_count += 1
        return original_loader(path)

    monkeypatch.setattr(config_module, "_load_models_from_yaml", counting_loader)

    with ThreadPoolExecutor(max_workers=8) as executor:
        snapshots = list(executor.map(lambda _: reloader.get(), range(32)))

    assert load_count == 1
    assert all(snapshot["test-model"]["display_name"] == "Updated concurrently" for snapshot in snapshots)


def test_load_valid_yaml(tmp_path):
    yaml_content = """
test-model:
  name: provider/test-model
  display_name: Test Model
  type: openrouter
  input_cost_per_mtok: 0.5
  output_cost_per_mtok: 2.0
  is_active: true
  temperature: 0.85
  base_model: Test Model
  preset_name: Temp 0.85
"""
    yaml_file = tmp_path / "models.yaml"
    yaml_file.write_text(yaml_content, encoding="utf-8")

    models = _load_models_from_yaml(yaml_file)

    assert "test-model" in models
    assert models["test-model"]["name"] == "provider/test-model"
    assert models["test-model"]["is_active"] is True
    assert models["test-model"]["temperature"] == 0.85


def test_load_multiple_models(tmp_path):
    yaml_content = """
model-a:
  name: provider/a
  display_name: Model A
  type: openrouter
  input_cost_per_mtok: 0.1
  output_cost_per_mtok: 0.4
  is_active: true

model-b:
  name: provider/b
  display_name: Model B
  type: openrouter
  input_cost_per_mtok: 1.0
  output_cost_per_mtok: 5.0
  is_active: false
"""
    yaml_file = tmp_path / "models.yaml"
    yaml_file.write_text(yaml_content, encoding="utf-8")

    models = _load_models_from_yaml(yaml_file)

    assert len(models) == 2
    assert models["model-a"]["is_active"] is True
    assert models["model-b"]["is_active"] is False


def test_missing_required_field(tmp_path):
    yaml_content = """
test-model:
  name: provider/test-model
  display_name: Test Model
  is_active: true
"""
    yaml_file = tmp_path / "models.yaml"
    yaml_file.write_text(yaml_content, encoding="utf-8")

    with pytest.raises(ValueError, match="missing required fields"):
        _load_models_from_yaml(yaml_file)


def test_is_active_must_be_bool(tmp_path):
    yaml_content = """
test-model:
  name: provider/test-model
  display_name: Test Model
  type: openrouter
  input_cost_per_mtok: 0.1
  output_cost_per_mtok: 0.4
  is_active: "yes"
"""
    yaml_file = tmp_path / "models.yaml"
    yaml_file.write_text(yaml_content, encoding="utf-8")

    with pytest.raises(ValueError, match="'is_active' must be a boolean"):
        _load_models_from_yaml(yaml_file)


def test_cost_must_be_number(tmp_path):
    yaml_content = """
test-model:
  name: provider/test-model
  display_name: Test Model
  type: openrouter
  input_cost_per_mtok: "free"
  output_cost_per_mtok: 0.4
  is_active: true
"""
    yaml_file = tmp_path / "models.yaml"
    yaml_file.write_text(yaml_content, encoding="utf-8")

    with pytest.raises(ValueError, match="'input_cost_per_mtok' must be a number"):
        _load_models_from_yaml(yaml_file)


def test_file_not_found(tmp_path):
    with pytest.raises(FileNotFoundError, match=r"models\.yaml not found"):
        _load_models_from_yaml(tmp_path / "nonexistent.yaml")


def test_empty_yaml(tmp_path):
    yaml_file = tmp_path / "models.yaml"
    yaml_file.write_text("", encoding="utf-8")

    with pytest.raises(ValueError, match="non-empty mapping"):
        _load_models_from_yaml(yaml_file)


def test_non_dict_entry(tmp_path):
    yaml_content = """
test-model: just-a-string
"""
    yaml_file = tmp_path / "models.yaml"
    yaml_file.write_text(yaml_content, encoding="utf-8")

    with pytest.raises(ValueError, match="expected mapping"):
        _load_models_from_yaml(yaml_file)


def test_reasoning_dict_preserved(tmp_path):
    yaml_content = """
test-model:
  name: provider/test-model
  display_name: Test Model
  type: openrouter
  input_cost_per_mtok: 0.5
  output_cost_per_mtok: 2.0
  is_active: true
  reasoning:
    effort: low
    max_tokens: 128
"""
    yaml_file = tmp_path / "models.yaml"
    yaml_file.write_text(yaml_content, encoding="utf-8")

    models = _load_models_from_yaml(yaml_file)

    assert models["test-model"]["reasoning"] == {"effort": "low", "max_tokens": 128}


def test_optional_fields_not_required(tmp_path):
    yaml_content = """
test-model:
  name: provider/test-model
  display_name: Test Model
  type: openrouter
  input_cost_per_mtok: 0.5
  output_cost_per_mtok: 2.0
  is_active: false
"""
    yaml_file = tmp_path / "models.yaml"
    yaml_file.write_text(yaml_content, encoding="utf-8")

    models = _load_models_from_yaml(yaml_file)

    assert "temperature" not in models["test-model"]
    assert "reasoning" not in models["test-model"]
    assert "timeout" not in models["test-model"]


def test_production_models_yaml_loads():
    models = _load_models_from_yaml()

    assert len(models) >= 30
    active = {k: v for k, v in models.items() if v["is_active"]}
    assert len(active) > 0

    for key, model in models.items():
        assert model["name"], f"Model '{key}' has empty name"
        assert model["display_name"], f"Model '{key}' has empty display_name"
        assert model["type"] == "openrouter", f"Model '{key}' has unexpected type"
        assert model["input_cost_per_mtok"] >= 0
        assert model["output_cost_per_mtok"] >= 0


def test_inactive_models_have_deactivation_reason():
    """All inactive models in production yaml should have a deactivation_reason."""
    models = _load_models_from_yaml()

    inactive = {k: v for k, v in models.items() if not v["is_active"]}
    assert len(inactive) > 0

    missing = [k for k, v in inactive.items() if not v.get("deactivation_reason")]
    assert not missing, f"Inactive models missing deactivation_reason: {', '.join(sorted(missing))}"


def test_active_models_do_not_need_deactivation_reason():
    """Active models should not have a deactivation_reason set."""
    models = _load_models_from_yaml()

    active = {k: v for k, v in models.items() if v["is_active"]}
    with_reason = [k for k, v in active.items() if v.get("deactivation_reason")]
    assert not with_reason, f"Active models should not have deactivation_reason: {', '.join(sorted(with_reason))}"


def test_multiple_validation_errors(tmp_path):
    yaml_content = """
model-a:
  name: provider/a
  is_active: true

model-b:
  name: provider/b
  display_name: Model B
  type: openrouter
  input_cost_per_mtok: 0.1
  output_cost_per_mtok: 0.4
  is_active: "yes"
"""
    yaml_file = tmp_path / "models.yaml"
    yaml_file.write_text(yaml_content, encoding="utf-8")

    with pytest.raises(ValueError, match="missing required fields") as exc_info:
        _load_models_from_yaml(yaml_file)

    error_msg = str(exc_info.value)
    assert "model-a" in error_msg
    assert "model-b" in error_msg


def test_mandatory_reasoning_models_not_set_to_none():
    """Mandatory-reasoning models must not send effort=none (causes OpenRouter 400).

    Per OpenRouter GET /api/v1/models, these models report reasoning.mandatory=true,
    so effort=none is rejected. They must use the lowest supported effort level:
      - Gemini 3.7 Flash (mandatory): supports high,medium,low -> low or medium
      - Muse Glimmer 30B (mandatory): supports xhigh,high,medium,low -> low
      - Muse Spark 1.2 (mandatory): supports xhigh,high,medium,low,minimal -> minimal

    DeepSeek V4 Pro/Flash (mandatory=false) legitimately use none.
    """
    models = _load_models_from_yaml()

    # Each entry: (model key, exact expected reasoning effort)
    expected_effort = {
        "gemini-3.7-flash-t1.0": "low",
        "gemini-3.7-flash-t0.3": "low",
        "gemini-3.7-flash-medium-t1.0": "medium",
        "muse-glimmer-30b-t1.0": "low",
        "muse-glimmer-30b-t0.3": "low",
        "muse-spark-1.2-t1.0": "minimal",
        "muse-spark-1.2-t0.3": "minimal",
    }

    for key, effort in expected_effort.items():
        assert key in models, f"Expected mandatory-reasoning model '{key}' to exist in models.yaml"
        reasoning = models[key].get("reasoning")
        assert reasoning is not None, (
            f"Mandatory-reasoning model '{key}' must define a reasoning block"
        )
        actual = reasoning.get("effort")
        assert actual == effort, (
            f"Mandatory-reasoning model '{key}' must use effort='{effort}' "
            f"(got '{actual}'); effort='none' triggers OpenRouter 400 errors"
        )

    # DeepSeek V4 Pro/Flash are mandatory=false and must remain on none.
    deepseek_none_models = [
        "deepseek-v4-pro-0813-t1.0",
        "deepseek-v4-pro-0813-t0.3",
        "deepseek-v4-flash-0731-t1.0",
        "deepseek-v4-flash-0731-t0.3",
    ]
    for key in deepseek_none_models:
        assert key in models, f"Expected DeepSeek model '{key}' to exist in models.yaml"
        reasoning = models[key].get("reasoning")
        assert reasoning is not None, f"DeepSeek model '{key}' should define a reasoning block"
        assert reasoning.get("effort") == "none", (
            f"DeepSeek model '{key}' (mandatory=false) must keep effort='none'"
        )


def test_reasoning_effort_is_visible_in_preset_labels():
    """Explicit reasoning settings must not be hidden behind generic labels."""
    models = _load_models_from_yaml()

    labels = {
        "none": ("No Reasoning", "No Thinking"),
        "minimal": ("Minimal Reasoning", "Minimal Thinking"),
        "low": ("Low Reasoning", "Low Thinking"),
        "medium": ("Medium Reasoning", "Medium Thinking"),
    }
    for key, model in models.items():
        effort = (model.get("reasoning") or {}).get("effort")
        if effort not in labels:
            continue

        expected_labels = labels[effort]
        preset_name = model.get("preset_name") or ""
        assert any(label in preset_name for label in expected_labels), (
            f"Model '{key}' uses reasoning effort='{effort}', but preset_name "
            f"does not include one of {expected_labels}"
        )
