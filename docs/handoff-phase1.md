# Handoff: Phase 1 Complete — Phases 2-4 Pending

## Status

Phase 1 (Glicko-2 Migration) is complete and committed. All 50 tests pass (38 Glicko-2 + 12 existing config tests).

## What Was Done in Phase 1

### Schema Changes (`app/models.py`)
- `ModelELO`: added `rating_deviation` (FLOAT, default 350.0), `volatility` (FLOAT, default 0.06), `legacy_elo_rating` (FLOAT, nullable), `last_comparison_at` (DATETIME, nullable)
- `PairwiseComparison`: added `score` (FLOAT, nullable)

### Config (`app/config.py`)
- Glicko-2 parameters: `GLICKO_TAU=0.5`, `GLICKO_MIN_RD=80`, `GLICKO_C_PER_WEEK≈48.6`, `GLICKO_INITIAL_RD=350`, `GLICKO_INITIAL_VOLATILITY=0.06`
- Cost tier thresholds: `COST_CHEAP_THRESHOLD=3.0`, `COST_EXPENSIVE_THRESHOLD=10.0`
- Difficulty thresholds: `DIFFICULTY_EASY_THRESHOLD=0.3`, `DIFFICULTY_HARD_THRESHOLD=-0.3`
- Stratified selection: `STRATIFIED_TARGETS={"easy": 2, "medium": 5, "hard": 2, "unknown": 1}`
- `MAX_EXPENSIVE_GROUPS=2`

### Glicko-2 Algorithm (`app/services/elo_service.py`)
- `_glicko2_update()`: core algorithm with volatility iteration, time-based RD decay, MIN_RD floor
- `ELOService._apply_glicko2()`: single-comparison processing with `weeks_inactive` from `_weeks_since_last_comparison()`
- `ELOService.update_ratings()`, `record_tie()`, `record_comparison()`: public API (backward compatible — explicit comparisons default to score=1.0/0.5)
- `ELOService.rebuild_ratings_from_comparisons()`: wipes ModelELO, replays all comparisons in stable order (created_at asc, id asc) with inter-comparison time decay per model
- `ELOService.derive_from_existing_votes()`: one-time migration function using fractional scoring and tie-skip logic

### Vote Service (`app/services/vote_service.py`)
- `_gap_to_score()`: maps star rating gap to fractional score (4→1.0, 3→0.95, 2→0.85, 1→0.70)
- `_should_skip_pair()`: skips both-3-star and both-(-1)-star pairs
- `_derive_pairwise_from_votes()`: deletes old derived comparisons, creates new ones directly (no incremental rating updates), then calls `rebuild_ratings_from_comparisons()` to ensure live ratings match stored comparisons
- `process_votes()`: after upserting votes, fetches ALL persisted votes for (user_id, query_id) and passes the complete set to derivation

### Migration (`init_db.py`)
- `_migrate_glicko2_columns()`: idempotent — checks column existence via `inspect()`, adds missing columns with ALTER TABLE. Backfill always runs (not gated on `added_any`), ensuring resumability. Tie backfill requires non-null `translation_a_id` AND `translation_b_id`.

### CLI (`app/cli.py`)
- `rebuild-ratings` command: triggers `rebuild_ratings_from_comparisons()` and prints updated rankings

### Tests (`tests/test_glicko2.py`)
- 38 tests: Glicko-2 algorithm (win/loss/tie/fractional/RD decay/MIN_RD floor), fractional scoring, tie-skip logic, ELOService integration, rebuild idempotency/stable order/matches-incremental (with RD and volatility comparison), vote derivation with delete-before-re-derive, re-vote rebuilds ratings, partial vote preserves all comparisons

### Documentation
- ADRs: `docs/adr/0001-glicko-2-replaces-elo.md`, `docs/adr/0002-fractional-scores-for-derived-comparisons.md`, `docs/adr/0003-single-user-design-constraints.md`
- `docs/elo-improvement-plan.md`: full plan with all phases
- `CONTEXT.md`: project context

## Known Issues
- `ty check` reports ~30 SQLAlchemy `Column[Unknown]` vs runtime type mismatches — standard pattern in this codebase, not actionable without Mypy plugin or typed-column wrappers.

## Pending Phases

### Phase 2: Pair Selection Improvements
1. **Quick Compare filter** — only show pairs where both translations have ≥2-star rating and gap <2. Join votes to current user's ratings only.
2. **Pair-level comparison counts** — count explicit comparisons only (not derived), via translation model name joins (winner/loser columns are NULL for ties).
3. **Composite pair priority** — remove `limit(100)` random batch. Fetch all uncompared pairs, apply priority: ELO closeness 30%, RD uncertainty 25%, pair hunger 25%, same-rated bonus +0.3 additive.

### Phase 3: Query Intelligence
1. **Query difficulty** — model-adjusted residuals (actual_rating - model_global_avg). Tiers: easy ≥+0.3, hard ≤-0.3, medium in between, unknown if <3 votes or <2 models.
2. **Stratified query selection** — 2 easy, 5 medium, 2 hard, 1 unknown per session. Backfill from remaining pool if tiers exhausted.
3. **Cost-aware model selection** — max 2 expensive base model groups per session. Cost tiers: cheap ≤$3/Mtok, mid $3-$10, expensive >$10.
4. **Fix usage stats** — count voted translations, not all translations.

### Phase 4: Polish
1. **Confidence-weighted leaderboard** — convex blend: `combined = normalized_glicko * confidence + normalized_avg_score * (1 - confidence)` where `confidence = 1 - (RD/350)`.
2. **3-star tie refinement** — when difficulty tracking is available, stop skipping both-3-star pairs on non-trivial queries. Add dashboard metrics.

## Key Files for Next Phases
- `app/blueprints/main.py` — pair selection, Quick Compare endpoint
- `app/blueprints/stats.py` — leaderboard, usage stats
- `app/services/elo_service.py` — rating queries, `get_all_rankings()`
- `app/services/stats_service.py` — stats calculations
- `app/services/cost_service.py` — cost tier logic
- `app/config.py` — all thresholds and targets already defined
- `app/repositories/query_repository.py` — query selection logic
- `app/repositories/translation_repository.py` — translation fetching
- `static/js/compare.js` — Quick Compare frontend
- `templates/compare.html` — Quick Compare UI
- `templates/stats.html` — leaderboard/stats UI
