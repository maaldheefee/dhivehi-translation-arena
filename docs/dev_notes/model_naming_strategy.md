# Model Configuration Guide

Model definitions live in `models.yaml` at the project root. The `Config` class in `app/config.py` loads and validates them at startup.

## Key Naming Convention

Database keys follow the pattern `{base-model}[-{reasoning}]-t{temp}`:

```
gemini-2.0-flash-t0.1
gemini-3-flash-low-t1.0
claude-opus-4.5-t0.85
```

Temperature is always explicit in the key so the identifier is self-documenting and never needs to change.

## Configuration Flags

| Flag          | Type   | Purpose                                        |
| ------------- | ------ | ---------------------------------------------- |
| `is_active`   | `bool` | Can be selected for new translations           |
| `is_hidden`   | `bool` | Hidden from UI selectors (data kept in stats)  |

**Flag combinations:**

- `is_active: true, is_hidden: false` — Available and visible (normal state)
- `is_active: false, is_hidden: false` — Deprecated but visible in stats
- `is_active: false, is_hidden: true` — Fully hidden from UI

## Required Fields per Model

```yaml
model-key:
  name: "provider/model-id"        # Upstream model ID sent to OpenRouter
  display_name: "Model Display"    # Shown in the UI
  type: "openrouter"               # Only "openrouter" is supported
  input_cost_per_mtok: 0.5         # Cost per million input tokens (USD)
  output_cost_per_mtok: 2.0        # Cost per million output tokens (USD)
  is_active: true                  # Whether model is selectable
```

## Optional Fields

```yaml
  temperature: 0.85                # Overrides DEFAULT_TEMPERATURE (0.1)
  rate_limit: 10                   # Max requests per 60s window
  timeout: 180.0                   # API timeout in seconds (default 90)
  thinking_budget: 4096            # For thinking models
  reasoning:                       # OpenRouter reasoning config
    effort: low
    max_tokens: 128
  base_model: "Gemini 3 Flash"     # Groups variants together
  preset_name: "Low Reasoning"     # Variant label in the UI
  is_hidden: false                 # Hide from selectors
```

## Adding a New Model

1. Add the entry to `models.yaml`
2. Run `uv run pytest tests/test_config.py` to validate
3. Restart the application

## Deprecating a Model

Set `is_active: false` in `models.yaml`. Historical data is preserved in stats. To fully hide, also set `is_hidden: true`.

## Renaming a Model

See [model_renaming.md](model_renaming.md) for the step-by-step migration process using `scripts/rename_model.py`.
