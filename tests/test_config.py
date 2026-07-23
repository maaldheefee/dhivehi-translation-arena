import pytest

from app.config import _load_models_from_yaml


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
    with pytest.raises(FileNotFoundError, match="models.yaml not found"):
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

    missing = [
        k for k, v in inactive.items()
        if not v.get("deactivation_reason")
    ]
    assert not missing, f"Inactive models missing deactivation_reason: {', '.join(sorted(missing))}"


def test_active_models_do_not_need_deactivation_reason():
    """Active models should not have a deactivation_reason set."""
    models = _load_models_from_yaml()

    active = {k: v for k, v in models.items() if v["is_active"]}
    with_reason = [
        k for k, v in active.items()
        if v.get("deactivation_reason")
    ]
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
