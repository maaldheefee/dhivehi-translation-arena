# Dhivehi Translation Arena — Context

## Purpose

A tool for evaluating and ranking LLM translation quality for Arabic → Dhivehi.
A single user (the developer) rates translations from multiple models using
star ratings and optional pairwise A/B comparisons. The system derives
Glicko-2 ratings from this data to rank models by translation quality.

## Usage Pattern

- Used infrequently: bursts of activity when new models are released,
  then dormant for days or weeks.
- ~90%+ of all votes come from a single user.
- 43 predefined Arabic queries, 10 shown per session.
- 6 models shown per session (hard limit 10), grouped by base model.

## Ubiquitous Language

### Rating System

- **Glicko-2**: The rating system replacing standard ELO. Tracks three
  values per model: rating (skill estimate), RD (rating deviation =
  uncertainty), and volatility (rating stability over time).
- **RD (Rating Deviation)**: How uncertain the system is about a model's
  rating. Starts at 350 (max uncertainty), shrinks as comparisons
  accumulate. Floor at 80 to prevent overconfidence. Increases during
  dormancy via time-based decay (c ≈ 48.6/week).
- **Volatility**: How much a model's rating fluctuates between rating
  periods. Controlled by system constant τ = 0.5.
- **Rating Period**: Each comparison is processed immediately (no
  batching). Equivalent to a degenerate Glicko-2 period with 1 game.
- **MIN_RD**: Floor of 80. Prevents ratings from becoming unresponsive
  after many comparisons.

### Comparisons

- **Derived Comparison**: Pairwise comparison inferred from star ratings.
  If Translation A gets 3★ and B gets 1★, A wins over B. Uses fractional
  scores based on the rating gap. Derived comparisons are replaced (deleted
  and re-derived) when a user changes their star rating for a query.
  Explicit comparisons are immutable events.
- **Explicit Comparison**: Direct user choice in Quick Compare mode.
  User picks winner, loser, or tie. Always binary score (1.0/0.0/0.5).
- **Fractional Score**: Glicko-2 game score on [0, 1] continuum. For
  derived comparisons, the rating gap determines the score:
  gap=4 → 1.0, gap=3 → 0.95, gap=2 → 0.85, gap=1 → 0.70.
- **Gap**: Absolute difference in star ratings between two translations.
  Rating scale is 3, 2, 1, -1 (NOT 3, 2, 1, 0).
  Examples: 3 vs 2 -> gap 1, 3 vs 1 -> gap 2, 2 vs -1 -> gap 3, 3 vs -1 -> gap 4.
  Larger gap = more confident win = score closer to 1.0.
- **Score**: The value fed to Glicko-2 for each comparison. Stored in
  `PairwiseComparison.score` column. Winner gets `score`, loser gets
  `1 - score`.

### Star Ratings

- **Star Rating Scale**: 3 = Excellent, 2 = Meaning Correct,
  1 = Understandable, -1 = Trash.
- **Tie Logic**: Both 3★ → skip (perfection = query ease, not skill).
  Both -1★ → skip (mutual failure = query signal, not model signal).
  Both 1★ or both 2★ → tie (score 0.5). Both 3★ on non-easy queries →
  tie (once difficulty tracking is implemented).

### Pair Selection (Quick Compare)

- **Quick Compare Filter**: Only shows pairs where both translations are
  rated ≥ 2★ AND star rating gap < 2. Filters out obvious pairs and
  low-quality translations.
- **Pair Priority**: Composite score combining ELO closeness (30%),
  uncertainty via RD (25%), pair hunger (25%), and same-rated bonus
  (+0.3 additive). Higher score = more likely to be shown.
- **Same-Rated Bonus**: Flat +0.3 added to pair priority when both
  translations share the same star rating. Highest-value signal because
  A/B breaks ties that star ratings cannot resolve.

### Model Selection (Main Arena)

- **Base Model Grouping**: Models are grouped by `base_model` field.
  Preset variants (temperature, reasoning) of the same underlying model
  are kept together to enable quality comparisons between configurations.
- **Cost Tiers**: Cheap (≤ $3/Mtok output), Mid ($3-$10), Expensive
  (> $10). Max 2 expensive base model groups per session.
- **Usage Stats**: Count of translations that have received at least one
  vote (not total translations generated). Used to prioritize
  under-rated models.

### Query Difficulty

- **Model-Adjusted Residual**: Query difficulty measured by how much
  each model underperforms its own global average on that query.
  Removes confound of which models were tested on which queries.
  `residual = actual_rating - model_global_avg`. Difficulty =
  mean of negative residuals across all votes on that query.
- **Difficulty Tiers**: Easy (avg residual ≥ +0.3), Hard (≤ -0.3),
  Medium (in between). Requires ≥ 3 votes from ≥ 2 models before
  classification; otherwise "unknown".
- **Stratified Query Selection**: 2 easy, 5 medium, 2 hard, 1 unknown
  per session. Couples with cost-aware selection: expensive models
  get hard queries, cheap models get easy/medium.

### Leaderboard

- **Confidence-Weighted Blend**: `glicko_component = normalized_glicko
  × confidence` where `confidence = 1 - (RD / 350)`. Star component
  fills the gap when RD is high. When RD is low (confident), Glicko-2
  dominates. When RD is high (uncertain), star ratings dominate.
- **Legacy ELO**: Previous ELO ratings preserved in
  `legacy_elo_rating` column for rollback and comparison.

### Data Architecture

- **Raw Data**: `Vote` (star ratings) and `PairwiseComparison`
  (pairwise results with scores) are the source of truth.
- **Derived Data**: `ModelELO` (Glicko-2 ratings) is computed from
  raw comparison data. Can be rebuilt at any time by replaying all
  `PairwiseComparison` records.
- **Rebuild**: `rebuild_ratings_from_comparisons()` function replays
  all comparisons through Glicko-2 to reconstruct ratings from scratch.

## Key Files

- `app/services/elo_service.py` — Glicko-2 rating logic
- `app/services/vote_service.py` — Star rating processing, derived
  comparison generation with fractional scores
- `app/blueprints/main.py` — Model selection, pair selection,
  query selection
- `app/services/stats_service.py` — Leaderboard computation,
  usage stats, query difficulty
- `app/models.py` — `Vote`, `PairwiseComparison`, `ModelELO` models
- `app/config.py` — `MAX_MODELS_SELECTION` and app configuration
- `models.yaml` — Model definitions with cost, base_model, presets
- `app/predefined_queries.py` — 43 predefined Arabic test queries
