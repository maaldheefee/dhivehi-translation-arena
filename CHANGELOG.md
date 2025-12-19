# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Localization**: Global translation helper `t()` and `window.translations` injection in `base.html` for consistent access to localized strings across all scripts.
- **Localization**: Added missing localization keys for Compare UI, stats headers, and toast messages.
- **UI**: New glassmorphism and premium UI utility classes in CSS.
- **Stats**: Vote distribution (excellent/good/okay/rejected) now included in JSON export for detailed analysis.
- **Copy Buttons**: Unified JSON and Analysis Prompt copy buttons across all three pages (Main, Compare, Stats) with consistent styling and placement.
- **Agent**: Added `/commit` workflow for standardized commit messages and CHANGELOG updates.

### Changed
- **UI**: Complete visual overhaul for a "Premium" aesthetic using a slate/blue color palette, cleaner shadows, and improved input focus states.
- **UI**: Combined "Instructions", "Configure Models", and "Predefined Queries" into a single cohesive "Controls Card" on the main page.
- **UI**: Refined the "Filter Models" button in the Compare UI with a new icon and cleaner styling.
- **Algorithm**: Bang-for-buck scoring now uses logarithmic normalization instead of linear. This spreads values more evenly across the 0-10 range.
- **Stats**: Enhanced analysis prompt with comprehensive evaluation framework including cost-effectiveness, configuration impact, and vote distribution insights.
- **CI/CD**: Updated deployment webhook to use dedicated secrets `DEPLOY_WEBHOOK_TOKEN` and `DEPLOY_WEBHOOK_URL` for better security and flexibility.
- **Project Structure**: Renamed `CHANGES.md` to `CHANGELOG.md` to follow standard conventions and updated `.gitignore` to track `.agent/` configuration.
- **DevOps**: Added detailed setup and usage instructions to `dhivehi-translation-arena.service` template.

### Fixed
- **Localization**: Resolved missing placeholders (`stats_subheader`, `option_a`, etc.) in the Compare and Stats interfaces.
- **UI**: Fixed visibility and dark mode support for the advanced model filter button and panel.
- **RTL**: Improved RTL spacing and alignment for collapsible summary icons.
- **Docs**: Fixed outdated references to `DEPLOYMENT.md`, non-existent `MODEL_NAMING_ANALYSIS.md`, and incorrect database filename `translations.db`.


## [0.2.0] - 2025-12-18

### Added
- **Core Feature**: "Funnel" ranking strategy. Star ratings now automatically generate approximate pairwise ELO comparisons (Derived Ties) to feed the active learning queue.
- **CLI**: New `flask derive-elo` command to backfill pairwise comparisons from historical vote data.
- **Docs**: Comprehensive methodology documentation with academic rigor, mermaid diagrams, and design rationale.
- **Docs**: Documentation restructuring. Moved User docs to `/docs` and Dev notes to `/docs/dev_notes`.
- **UI**: Advanced ELO Pairing filter to "force include" specific models in comparisons.
- **Stats**: "Projected Cost (100k words)" and "Bang for Buck" metrics.
- **Config**: "Low Temperature" variants (0.1) for Gemini and Claude models.

### Changed
- **Algorithm**: Combined Score weighting changed from 50/50 to **40% Rating / 60% ELO** to correct for optimism bias in user ratings.
- **Algorithm**: Balanced Model Selection now uses bucketed randomization to ensure fair vendor representation while prioritizing low-usage models.
- **Algorithm**: ELO active learning now prioritizes pairs with close ELO ratings (including derived ties) for explicit comparison.
- **UI**: Standardized all rating descriptions across EN/DV i18n, methodology docs, and copy-to-clipboard rubric.
- **UI**: Significant visual polish to model selector, main page layout, and stats grid.
- **UI**: Combined scores now displayed as 0-100 percentage with color coding.
- **Refactor**: Renamed `DEPLOYMENT.md` to `docs/deployment.md`.

### Fixed
- **Authentication**: Resolved `ProxyFix` issues for Cloudflare Tunnel.
- **Streaming**: Fixed buffering issues with `X-Accel-Buffering: no` headers.
- **Stability**: Pending translations are correctly marked as failed on stream error, preventing UI hangs.
- **Sorting**: Fixed numeric sorting for "Bang for Buck" stats column.
- **Localization**: Complete Eng/Dhivehi support for all new comparison UI elements.

## [1.0.0] - 2025-12-01

### Added
- Initial release of Dhivehi Translation Arena.
- Basic Voting (1-3 Stars) and ELO Ranking System.
- Google Gemini and Anthropic Claude integration.
- Dark/Light mode support.
