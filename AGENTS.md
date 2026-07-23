# Agent Guide: Adding a New Model

This guide is for AI agents (and humans) adding a new LLM to the Dhivehi Translation Arena.

## Workflow

### 1. Research the Model Online

Before adding a model, research its recommended parameters:

- **Search for the model's official documentation** (e.g., Google AI docs, Anthropic docs, OpenAI docs, DeepSeek docs).
- **Find the recommended temperature** for general/text generation use. Most modern models recommend 1.0. Some older models default to 0.7-0.9.
- **Check if the model supports reasoning/thinking** and what the configuration options are (effort levels, max_tokens, etc.).
- **Find the pricing** — input and output cost per million tokens (check OpenRouter pricing page or the provider's pricing page).
- **Check the OpenRouter model ID** — this goes in the `name` field (e.g., `google/gemini-3-flash-preview`).

### 2. Add Model Entries to `models.yaml`

Always add **at least two variants**:

1. **Recommended temperature** — the model's recommended default (use 1.0 if no specific recommendation exists).
2. **Low temperature** — a low-temp variant (0.1 or 0.3) for comparison.

If the model supports reasoning/thinking, consider adding reasoning variants too.

#### Example Entry

```yaml
# ==================== Example Model ====================

example-model-t1.0:
  name: provider/example-model
  display_name: Example Model (T1.0)
  type: openrouter
  input_cost_per_mtok: 1.0
  output_cost_per_mtok: 5.0
  is_active: true
  timeout: 180.0
  base_model: Example Model
  temperature: 1.0
  preset_name: Default, Temp 1.0

example-model-t0.3:
  name: provider/example-model
  display_name: Example Model (T0.3)
  type: openrouter
  input_cost_per_mtok: 1.0
  output_cost_per_mtok: 5.0
  is_active: true
  timeout: 180.0
  base_model: Example Model
  temperature: 0.3
  preset_name: Temp 0.3
```

### 3. Naming Convention

Database keys follow: `{base-model}[-{reasoning}]-t{temp}`

- `gemini-3-flash-t1.0` — base model at temp 1.0
- `gemini-3-flash-low-t1.0` — base model with low reasoning at temp 1.0
- `claude-opus-4.5-t0.1` — base model at temp 0.1

Temperature is always explicit in the key so the identifier is self-documenting.

### 4. Required Fields

| Field                   | Type   | Purpose                                  |
| ----------------------- | ------ | ---------------------------------------- |
| `name`                  | str    | Upstream model ID sent to OpenRouter     |
| `display_name`          | str    | Shown in the UI                          |
| `type`                  | str    | Always `openrouter`                      |
| `input_cost_per_mtok`   | float  | Cost per million input tokens (USD)      |
| `output_cost_per_mtok`  | float  | Cost per million output tokens (USD)     |
| `is_active`             | bool   | Whether model is selectable for new runs |
| `base_model`            | str    | Groups variants together in stats        |
| `preset_name`           | str    | Variant label in the UI                  |
| `temperature`           | float  | Explicit temperature (always set)        |

### 5. Optional Fields

| Field             | Type    | Purpose                                      |
| ----------------- | ------- | -------------------------------------------- |
| `is_hidden`       | bool    | Hidden from UI selectors (data kept in stats)|
| `rate_limit`      | float   | Max requests per 60s window                   |
| `timeout`         | float   | API timeout in seconds (default 90)           |
| `thinking_budget` | int     | For thinking models                           |
| `reasoning`       | dict    | OpenRouter reasoning config (effort, max_tokens) |

### 6. Temperature Convention

- **Default for new models: 1.0** — most modern models (Gemini 3+, Claude 4+, GPT-5+) recommend 1.0.
- **Always add a low-temp variant** (0.1 or 0.3) to test whether lower temperature improves translation consistency.
- For reasoning/thinking models, use the model's recommended temperature (often 1.0) and add a low-temp reasoning variant.
- Older models that used 0.85 as default are kept as-is for historical data.

### 7. Validate and Deploy

```bash
uv run pytest tests/test_config.py
```

Then restart the application.

### 8. Deprecating a Model

Set `is_active: false` in `models.yaml`. Historical data is preserved in stats. To fully hide, also set `is_hidden: true`.

For renaming, see `docs/dev_notes/model_renaming.md`.

## Key Files

- `models.yaml` — Model definitions
- `app/config.py` — Config loader and validation
- `docs/dev_notes/model_naming_strategy.md` — Detailed naming strategy
- `docs/dev_notes/model_renaming.md` — Model rename migration process
- `scripts/rename_model.py` — Rename script
