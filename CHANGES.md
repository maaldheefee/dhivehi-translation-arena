# Changelog

## December 2025

### New Features
- **User Management**: Implemented `flask add-user`, `flask remove-user` CLI commands, and `manage_users.py` script.
- **LLM Integration**: Added Gemini 3 Pro and Claude Opus 4.5 via OpenRouter. Implemented model presets (temperature, reasoning budget).
- **Stats Improvements**: Added "Projected Cost (100k words)" and "Bang for Buck" metrics to stats page.

### Improvements & Infrastructure
- **Environment Config**: Used ENV variables for paths and secrets. Updated Docker and Justfile for dev/prod parity.
- **CI/CD**: Added GitHub Action for Docker build and volume mounts in `compose.yml`.
- **Frontend Model Selection**: Limit display to 6 models max, prioritizing those with fewer usage data points.
- **Error Handling**: Improved LLM error handling (timeouts, max tokens). Allowed voting on successful responses even if some models fail.
- **Cleanup**: Removed native Gemini Client in favor of unified OpenRouter client.

### Fixes
- **UI Hang**: Fixed issue where UI hangs on stream error. Pending translations are now marked as failed, allowing voting on successful results.
- **Duplicate Handling**: Added warning badge for duplicate translation results from the same model to prevent redundant voting.

### Localization & Polish
- **Full Localization**: Implemented full English/Dhivehi support for all UI elements including badges, toasts, and tooltips.
- **Rating Tips**: Added descriptive tooltips for rating stars (1-3 stars) to guide better quality assessment.
- **UI Polish**: Unified UI components and fixed untranslated strings.
