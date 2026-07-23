# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Reports**: Added Gemini 3.1 Pro Deep Research report (2026-07-23) — comprehensive analysis of 37 LLM configurations for Arabic-to-Dhivehi translation covering performance ranking, longitudinal model evolution, temperature/reasoning configuration impact, cost-effectiveness, and qualitative syntactic evaluation.
- **Models**: Added Google Gemma 4 31B Instruct and Gemini 3.1 Flash Lite Preview models with T0.1 and T0.85 variants, plus a Gemma 4 "Default" variant with no explicit temperature or reasoning.
- **Models**: Added `google/gemma-4-26b-a4b-it` (Gemma 4 26B Instruct) with its default configuration.
- **UI/Footer**: Updated copyright year to a range (2025&ndash;2026) using proper typography.
- **Configuration**: New frontend settings system to hide specific models/presets from the UI and stats page, persisted in `localStorage`.
- **Configuration**: Added "Auto-select N models" setting to customize the number of models automatically picked for comparison.
- **UI**: Added a "Settings" gear icon and modal to manage visibility and auto-selection preferences.
- **Rating System**: Glicko-2 rating system replacing legacy ELO. New columns on `ModelELO` (`rating_deviation`, `volatility`, `legacy_elo_rating`, `last_comparison_at`) and `PairwiseComparison` (`score`). Config constants for tau, MIN_RD, c/week, initial RD/volatility, cost tiers, difficulty thresholds, and stratified selection targets.
- **Rating System**: Fractional scoring for derived comparisons based on star rating gap (1.0/0.95/0.85/0.70). Tie-skip logic for both-3-star and both-(-1)-star pairs.
- **Rating System**: `rebuild-ratings` CLI command to replay all comparisons from scratch in stable order (created_at asc, id asc) with time decay.
- **Rating System**: Idempotent startup migration in `init_db.py` — adds missing Glicko-2 columns via ALTER TABLE and backfills data. Always runs backfill for NULL values to ensure resumability.
- **Rating System**: ADRs 0001-0003 documenting Glicko-2 replacement, fractional scores, and single-user design constraints.
- **Tests**: 38 tests covering Glicko-2 algorithm, fractional scoring, tie logic, rebuild idempotency/stable order, re-vote consistency, and partial vote preservation.

### Changed
- **UI**: Major CSS refactor — expanded design token system (colors, shadows, radii, transitions, gradients), moved inline styles to semantic CSS classes, removed Tailwind utility classes from templates in favor of stylesheet-driven styling.
- **UI**: Cleaned up `base.html` header markup — title now links to home, removed inline SVG sizing, fixed indentation in user menu dropdown.
- **UI**: Refactored `compare.html` — replaced inline styles and utility classes with semantic classes (`compare-source`, `compare-card`, `compare-actions`, `filter-grid`, etc.).
- **UI**: Simplified `index.html` — consolidated duplicate detail classes, removed inline flex styles, added ARIA label to textarea.
- **UI**: Updated `compare.js` — replaced Tailwind utility class strings with semantic CSS class names for dynamically created elements.
- **Models**: `ModelELO` columns migrated to SQLAlchemy 2.0 typed `Mapped`/`mapped_column` style. `wins`, `losses`, `ties` are now non-nullable (`Mapped[int]`), eliminating defensive `or 0` guards across `elo_service.py`, `stats_service.py`, and `rename_model.py`.
- **API**: Updated `/get_available_models` and backend selection logic to respect user-defined exclusions and counts passed from the frontend.
- **Models**: Disabled `google/gemini-3-pro-preview` models as they have been discontinued.
- **Stats**: Leaderboard table and performance charts now dynamically respect user-hidden model settings.
- **Rating System**: `elo_service.py` completely rewritten — core `_glicko2_update()` algorithm, `ELOService` with single-comparison processing, time-based RD decay, `rebuild_ratings_from_comparisons()` with inter-comparison time decay.
- **Rating System**: `vote_service.py` — `_derive_pairwise_from_votes` now stores comparisons directly (no incremental rating updates) and triggers full rebuild after re-derivation. `process_votes` fetches ALL persisted votes for user+query after upserts, not just the current request subset.

### Fixed
- **UI**: Fixed RTL layout issues for toggle switches and table alignment in the stats dashboard.
- **Compare**: Handle 401 auth errors gracefully in compare page — shows toast notification and opens login dropdown instead of cryptic "Failed to fetch comparison" error.
- **Stats**: Fix SQLite ambiguous column error in `get_pair_comparison_counts()` — string labels in `group_by` caused FROM clause duplication with aliased joins. Switched to column expression references and explicit `select_from`.
- **Rating System**: Re-votes now rebuild all ratings from stored comparisons, ensuring live `ModelELO` matches the source of truth (previously stale ratings were stacked on top of deleted comparisons' effects).
- **Rating System**: Partial vote submissions no longer discard comparisons from omitted stored votes — derivation uses the complete persisted vote set.
- **Rating System**: Rebuild now applies time decay between consecutive comparisons per model using `created_at` timestamps, matching incremental processing.
- **Compare**: "Pairs remaining" counter in Quick Compare now only counts translations from active (non-deprecated) models, matching the actual pair selection logic.
- **Stats**: Bang-for-buck formula updated — models below 0.4 combined score now get 0, and the exponent reduced from 4 to 3 for a less extreme cost sensitivity curve.
- **Scripts**: Rewrote `analyze_data.py` to export structured JSON (leaderboard, temperature analysis, reasoning analysis, qualitative examples) using `stats_service` functions directly instead of raw ELO queries.
- **Rating System**: Migration backfill for tie scores requires non-null `translation_a_id` and `translation_b_id` — corrupt/incomplete rows are left untouched.
- **Rating System**: Migration backfill runs unconditionally every startup, not gated on whether columns were just added — ensures resumability after partial failure.
- **CLI**: `init-db` command now raises `RuntimeError` instead of `assert` for uninitialized engine (assert is stripped in optimized mode).
- **Migration**: Added backfill for NULL `wins`/`losses`/`ties` in `init_db.py` to support non-nullable column upgrade on existing databases.
- **Scripts**: `analyze_data.py` now guards against NULL `wins`/`losses`/`ties` with `or 0`.


## [0.3.0] - 2026-03-10

### Added
- **Localization**: Global translation helper `t()` and `window.translations` injection in `base.html` for consistent access to localized strings across all scripts.
- **Localization**: Added missing localization keys for Compare UI, stats headers, and toast messages.
- **UI**: New glassmorphism and premium UI utility classes in CSS.
- **Stats**: Vote distribution (excellent/good/okay/rejected) now included in JSON export for detailed analysis.
- **Copy Buttons**: Unified JSON and Analysis Prompt copy buttons across all three pages (Main, Compare, Stats) with consistent styling and placement.
- **UI/Stats**: Automatically hide inactive models from the stats table and chart by default, with a new toggle to show them.
- **Agent**: Added `/commit` workflow for standardized commit messages and CHANGELOG updates.
- **Security**: Hardened authentication by adding `@login_required` to sensitive data routes and removing insecure backdoors.
- **Algorithm**: Implemented "Trivial Query" ELO penalty protection to prevent high-quality models from losing ranking points on easy queries.
- **Performance**: Full refactor of the Stats dashboard and Pairwise generator to use server-side SQL aggregations and joins, eliminating $O(N)$ memory bottlenecks.
- **Typing**: Completed comprehensive type-hinting across blueprints, services, and models to achieve 100% `ty check` coverage.
- **Scripts**: Refactored `analyze_data.py` and `rename_model.py` with modern `pathlib` integration and improved error handling.
- **Code Quality**: Applied project-wide linting and formatting standards using `Ruff` (Python) and `Biome` (JS).

### Changed
- **UI**: Updated font weights to use numeric values (400, 700) and removed legacy `.woff` support in favor of modern `.woff2` only for better loading performance.
- **UI/Stats**: Upgraded the "show inactive models" toggle to a modern switch design and added missing Dhivehi translations.
- **UI**: Complete visual overhaul for a "Premium" aesthetic using a slate/blue color palette, cleaner shadows, and improved input focus states.
- **UI**: Combined "Instructions", "Configure Models", and "Predefined Queries" into a single cohesive "Controls Card" on the main page.
- **UI**: Refined the "Filter Models" button in the Compare UI with a new icon and cleaner styling.
- **Algorithm**: Bang-for-buck scoring now uses logarithmic normalization instead of linear. This spreads values more evenly across the 0-10 range.
- **Stats**: Enhanced analysis prompt with comprehensive evaluation framework including cost-effectiveness, configuration impact, and vote distribution insights.
- **CI/CD**: Updated deployment webhook to use dedicated secrets `DEPLOY_WEBHOOK_TOKEN` and `DEPLOY_WEBHOOK_URL` for better security and flexibility.
- **Project Structure**: Renamed `CHANGES.md` to `CHANGELOG.md` to follow standard conventions and updated `.gitignore` to track `.agent/` configuration.
- **DevOps**: Added detailed setup and usage instructions to `dhivehi-translation-arena.service` template.

### Fixed
- **Code Quality**: Resolved several type-checking ambiguities in `main.py` related to `werkzeug` vs `flask` response types and SQLAlchemy column casts.
- **DevOps**: Resolved `ModuleNotFoundError: No module named 'dotenv'` in production by deferring `load_dotenv()` import and making it conditional on non-production environments.
- **Localization**: Resolved missing placeholders (`stats_subheader`, `option_a`, etc.) in the Compare and Stats interfaces.
- **UI**: Fixed visibility and dark mode support for the advanced model filter button and panel.
- **UI/Stats**: Fixed a JavaScript syntax error that broke table sorting and chart rendering on the stats page.
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
