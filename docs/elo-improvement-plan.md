# ELO & Rating System Improvement Plan

## Report Date: 2026-07-22 (Revised 2026-07-22 after grilling session)

---

## Current System Summary

### Model Selection (Main Arena)

**File**: `app/blueprints/main.py:38-127`

- Selects up to `MAX_MODELS_SELECTION` (default 6, hard limit 10) models from active pool
- Groups models by `base_model` to keep preset variants together
- Prioritizes low-usage groups (usage = total translation count, not vote count)
- Buckets groups within 5 votes of each other, shuffles within buckets for randomness
- Selects whole groups in priority order; partial fill takes least-used variants
- Display order shuffled to eliminate position bias

### Query Selection

**File**: `app/blueprints/main.py:131-136`

- Pure random shuffle of 43 predefined queries, takes 10
- No difficulty stratification or coverage tracking

### ELO Pair Selection (Quick Compare)

**File**: `app/blueprints/main.py:405-558`

- Finds uncompared pairs (same `query_id`, different translations) for the current user
- Fetches random batch of 100 uncompared pairs
- Classifies: both-active > mixed > both-disabled (skipped)
- Sorts by ELO difference ascending (closest models first)
- Takes top 5 closest-ELO candidates, picks one randomly
- Shuffles A/B display position

### ELO Rating System

**File**: `app/services/elo_service.py:1-247`

- Standard ELO, K_FACTOR=32, default=1500
- Two comparison sources:
  - **Derived** (from star ratings): 3=Excellent, 2=Meaning Correct, 1=Understandable, -1=Trash
    - Rating difference → win/loss (binary)
    - Both 3★ → skip (perfection shouldn't penalize)
    - Equal rating < 3 → tie
  - **Explicit** (from Quick Compare): direct A/B choice or tie
- Derived comparisons generated in `app/services/vote_service.py:88-151` after every vote submission

### Star Rating as Primary Data Source

Star ratings are the **main data source** and provide unique advantages:

- **Class grouping**: Translations are grouped into quality classes (3★, 2★, 1★, -1★)
- **Multi-model coverage**: One vote session on 6 models produces up to 15 pairwise comparisons
- **Absolute quality signal**: Unlike A/B (relative only), star ratings give absolute quality context
- **Cross-family comparison**: Seeing 6 models from different families on the same query enables broad comparisons that A/B (2 models only) cannot provide

### Highest-Value Data: A/B on Same-Rated Translations

When two translations receive the **same star rating** but a user can still distinguish quality in a direct comparison, this is the **highest-value signal** because:

- Star ratings have coarse granularity (4 levels); many translations share the same rating
- A/B comparison breaks ties within a class, providing fine-grained discrimination
- This is exactly the signal that the rating system needs to separate models that appear equal in star ratings
- Example: Two models both get 3★ on a query → star rating says "tie" → A/B says "A is better" → rating system gets a precise signal

### Usage Context

- **Single user**: ~90%+ of all votes come from one person. No user reliability scoring needed.
- **Infrequent usage**: Bursts of activity when new models are released, then dormant for days/weeks.
- **~21 active models** across 12 base model groups.
- **43 predefined queries**, 10 shown per session.

---

## Problems Identified

### Model Selection

| # | Problem | Impact |
|---|---|---|
| M1 | Usage = translation count, not vote count | Models with many translations but few votes get deprioritized incorrectly |
| M2 | No ELO-awareness in selection | Doesn't prioritize close-rated model groups where comparisons are most informative |
| M3 | No cost-awareness | Expensive models (Claude Opus 4.6 at $5/$25) treated same as cheap ones (DeepSeek at $0.44/$0.87) |

### Pair Selection

| # | Problem | Impact |
|---|---|---|
| P1 | Only filters uncompared pairs per user, not globally | Doesn't leverage cross-user data — a pair compared by 1 user may still need more data |
| P2 | Random batch of 100 | May miss the globally best pair if pool is large |
| P3 | Top-5 closest ELO only | Ignores comparison count (uncertainty), query difficulty, cost |
| P4 | No pair-level comparison count tracking | Can't tell if Model A vs B has 2 comparisons or 200 |
| P5 | No filtering of obvious or low-quality pairs | Wastes user time comparing pairs where star ratings already give clear signal |

### Rating System

| # | Problem | Impact |
|---|---|---|
| E1 | Fixed K_FACTOR=32 | Over-reacts to outliers late in data collection; under-converges early |
| E2 | No uncertainty tracking | Can't distinguish "1500 ± 50" from "1500 ± 300" |
| E3 | Derived comparisons unweighted by gap | A 3★ vs -1★ gap (4 levels) produces same ELO update as 2★ vs 1★ (1 level) |
| E5 | Both-1★ or both-(-1)★ ties | May not be meaningful — both models failing doesn't mean they're equal |

### Query Selection

| # | Problem | Impact |
|---|---|---|
| Q1 | Pure random | Easy queries waste expensive model comparisons; hard queries may be underrepresented |
| Q2 | No difficulty tracking | Can't stratify by query complexity |
| Q3 | No coverage tracking | Some queries may be over-translated while others have sparse data |

---

## Agreed Improvements

### 1. Replace ELO with Glicko-2 [E1, E2]

Replace standard ELO with Glicko-2 rating system.

**Why Glicko-2 over adaptive K-factor**: Adaptive K-factor is a crude approximation of what Glicko-2 does continuously and precisely. Implementing adaptive K first would be throwaway work. Glicko-2 provides:
- Uncertainty tracking (RD — rating deviation)
- Confidence intervals
- Automatic K-factor adaptation based on data volume and time since last game
- Better sparse data handling

**Parameters**:
- System constant τ = 0.5 (moderate volatility, default)
- MIN_RD = 80 (floor to prevent overconfidence)
- Time-based RD increase: c ≈ 48.6/week (RD returns to near-max after ~1 year inactivity)
- DEFAULT_ELO = 1500.0 (starting rating, same as current)
- Initial RD = 350.0 (max uncertainty for new/migrated models)
- Initial volatility = 0.06 (Glicko-2 default)

**Processing model**: Each comparison processed immediately (no batching). Equivalent to degenerate Glicko-2 period with 1 game per period. MIN_RD floor compensates for faster RD decay.

**Deterministic replay order**: When processing multiple comparisons from a single vote submission (e.g., 15 derived pairs from 6 models), process in stable order: `created_at` ascending, then `id` ascending. This ensures rebuilds reproduce incremental state. A regression test must verify that `rebuild_ratings_from_comparisons()` produces identical ratings to incremental processing.

**Inactivity calculation**: Track `last_comparison_at` timestamp per model (updated on each comparison). RD time decay uses weeks since `last_comparison_at`, not weeks since last app start. Store as a column on `ModelELO` or derive from `MAX(PairwiseComparison.created_at)` per model.

**Migration**: Preserve existing `elo_rating` as starting Glicko-2 rating. Set RD=350, volatility=0.06. Copy current ratings to `legacy_elo_rating` column for rollback.

**Schema migration strategy**: The app uses `Base.metadata.create_all()` which creates missing tables but does not add columns to existing tables. There is no Alembic setup. Implement an idempotent startup migration in `init_db.py` that:
1. Checks for column existence via `PRAGMA table_info` (SQLite) or `information_schema` (PostgreSQL)
2. Runs `ALTER TABLE ADD COLUMN` for each missing column
3. Backfills `legacy_elo_rating` from `elo_rating` for existing rows
4. Runs inside a transaction with rollback on failure
5. Logs each step for auditability

```python
# Pseudocode for idempotent migration
required_columns = {
    'model_elo': [('rating_deviation', 'FLOAT DEFAULT 350.0'),
                  ('volatility', 'FLOAT DEFAULT 0.06'),
                  ('legacy_elo_rating', 'FLOAT')],
    'pairwise_comparisons': [('score', 'FLOAT')],
}
for table, columns in required_columns.items():
    existing = get_column_names(session, table)
    for col_name, col_type in columns:
        if col_name not in existing:
            session.execute(text(f'ALTER TABLE {table} ADD COLUMN {col_name} {col_type}'))
            session.commit()
            logger.info(f'Added column {col_name} to {table}')
# Backfill legacy_elo_rating
session.execute(text('UPDATE model_elo SET legacy_elo_rating = elo_rating WHERE legacy_elo_rating IS NULL'))
session.commit()
```

**Effort**: Medium
**Impact**: High — proper uncertainty tracking, better sparse data handling, handles dormancy naturally

---

### 2. Fractional Scores for Derived Comparisons [E3]

Replace binary win/loss with fractional Glicko-2 scores based on rating gap.

**Score mapping**:
```python
# Rating scale: 3, 2, 1, -1 (NOT 3, 2, 1, 0)
# Examples: 3 vs 2 -> gap 1, 3 vs 1 -> gap 2, 2 vs -1 -> gap 3, 3 vs -1 -> gap 4
gap = abs(r1 - r2)
if gap >= 4:    score = 1.0   # 3 vs -1, decisive
elif gap >= 3:  score = 0.95  # 2 vs -1, strong
elif gap >= 2:  score = 0.85  # 3 vs 1, or 1 vs -1, clear
else:           score = 0.70  # 3 vs 2, or 2 vs 1, marginal
```

Winner gets `score`, loser gets `1 - score`. Larger gap = more confident win = larger rating swing.

**Why not skip gap=1**: With sparse data and a single user, every comparison counts. The fractional score (0.70) already downweights marginal comparisons. Glicko-2's volatility parameter will capture inconsistency over time.

**Effort**: Low
**Impact**: Medium — improves noisy signal quality from derived comparisons

---

### 3. Tie-Handling Logic [E5]

| Both ratings | Action | Reasoning |
|---|---|---|
| 3★ vs 3★ | Skip (until difficulty tracking, then skip only on easy queries) | Perfection on easy queries is query-ease signal, not model-skill signal |
| 2★ vs 2★ | Tie (score 0.5) | Genuine equal competence |
| 1★ vs 1★ | Tie (score 0.5) | Genuine equal marginal competence |
| -1★ vs -1★ | Skip | Mutual failure is query signal, not model-skill signal |

Once query difficulty tracking is implemented (item 11), 3★-3★ on medium/hard queries becomes a tie (score 0.5) — both models nailed a challenging translation.

**Effort**: Low
**Impact**: Low — removes noise from garbage-tier and perfection ties

---

### 4. Store Score on PairwiseComparison

Add `score` column to store the fractional score per comparison.

```sql
ALTER TABLE pairwise_comparisons ADD COLUMN score FLOAT;
```

- Derived comparisons: store fractional score (0.70, 0.85, 0.95, 1.0)
- Explicit comparisons: store 1.0 (win), 0.0 (loss), 0.5 (tie)
- Existing rows: backfill based on outcome type, NOT blanket 1.0:
  - Non-null `winner_model` and `loser_model`: `score = 1.0` (binary win, old behavior)
  - Null `winner_model` and `loser_model` with both `translation_a_id` and `translation_b_id`: `score = 0.5` (tie)
  - Rows with null translations: skip (corrupt/incomplete data)

This makes `PairwiseComparison` self-contained — ratings can be rebuilt without re-deriving from `Vote`.

**Mutable vote semantics**: Votes are upserted — a user can change their star rating on a re-vote. However, `_derive_pairwise_from_votes()` currently appends new comparisons without removing old ones, creating stale/duplicate derived comparisons.

**Policy: replace derived comparisons on vote change**. Before deriving new comparisons for a `(user_id, query_id)` pair, delete all existing derived comparisons for that user and query:
```python
# In _derive_pairwise_from_votes, before the combinations loop:
session.query(PairwiseComparison).filter_by(
    user_id=user_id, query_id=query_id, source='derived'
).delete()
```
Explicit comparisons (`source='explicit'`) are immutable events — they are never deleted or modified by vote changes. A rebuild from `PairwiseComparison` will then reflect current vote state for derived comparisons plus the full history of explicit comparisons.

**Effort**: Low
**Impact**: Medium — enables clean rebuild, audit trail

---

### 5. Explicit A/B Comparisons: Binary Scores

Explicit Quick Compare comparisons always use binary scores:
- Win: 1.0
- Loss: 0.0
- Tie: 0.5

No fractional modulation. The act of choosing is the signal. Explicit comparisons are most valuable for same-rated pairs (gap=0) where derived comparisons produce nothing.

**Effort**: None (current behavior, just confirm)
**Impact**: N/A

---

### 6. Quick Compare Pair Filtering [P5]

Only show pairs in Quick Compare where:
- Both translations rated **≥ 2★**
- Star rating gap **< 2**

| Pair | Shown? |
|---|---|
| 3★ vs 3★ | Yes |
| 3★ vs 2★ | Yes |
| 2★ vs 2★ | Yes |
| 2★ vs 1★ | No (one <= 1 star) |
| 3★ vs 1★ | No (gap >= 2) |
| Any with -1★ | No |
| 1★ vs 1★ | No (both <= 1 star) |

Quick Compare becomes exclusively for "good vs good, hard to distinguish" pairs. Same-rated bonus in pair priority is simplified — all Quick Compare pairs are same-rated or adjacent by definition.

**Effort**: Low
**Impact**: High — eliminates low-value comparisons, saves user time

---

### 7. Uncertainty-Aware Pair Selection [P1, P3, P4]

Replace simple "closest ELO" with composite priority score using Glicko-2 RD:

```python
def pair_priority(elo_a, rd_a, elo_b, rd_b, pair_count, same_rating):
    # 1. ELO closeness (0 to 1)
    elo_diff = abs(elo_a - elo_b)
    elo_closeness = 1 / (1 + elo_diff / 100)

    # 2. Uncertainty via RD (0 to 1)
    avg_rd = (rd_a + rd_b) / 2
    uncertainty = min(1.0, avg_rd / 350)

    # 3. Pair hunger (0 to 1)
    pair_hunger = 1 / (1 + pair_count)

    # 4. Same-rated bonus (additive)
    same_rated_bonus = 0.3 if same_rating else 0.0

    return (elo_closeness * 0.30
          + uncertainty * 0.25
          + pair_hunger * 0.25
          + same_rated_bonus)
```

**Weights**: ELO closeness 30%, uncertainty 25%, pair hunger 25%, same-rated bonus +0.3 additive.

Requires tracking pair-level comparison counts (next item).

**Effort**: Medium
**Impact**: High — maximizes information gain per comparison

---

### 8. Track Pair-Level Comparison Counts [P4]

Add a query to count global comparisons per model pair:

The proposed `min(winner_model, loser_model)` grouping fails for ties — both columns are NULL, collapsing all ties into a single `(NULL, NULL)` group.

**Fix: use translation model names, not winner/loser columns**. Join through `translation_a_id` and `translation_b_id` to get model names independently of outcome:
```python
t_a = aliased(Translation)
t_b = aliased(Translation)
pair_counts = db_session.query(
    func.least(t_a.model, t_b.model).label("m1"),
    func.greatest(t_a.model, t_b.model).label("m2"),
    func.count().label("count")
).join(t_a, t_a.id == PairwiseComparison.translation_a_id) \
 .join(t_b, t_b.id == PairwiseComparison.translation_b_id) \
 .filter(PairwiseComparison.translation_a_id.isnot(None),
         PairwiseComparison.translation_b_id.isnot(None)) \
 .group_by("m1", "m2").all()
```

**Source specification**: `pair_count` counts **explicit comparisons only** (`source='explicit'`). Derived comparisons are abundant (15+ per session) and would swamp pair hunger, suppressing the same-rated explicit comparisons the plan calls highest-value. Add `.filter(PairwiseComparison.source == 'explicit')` to the query.

Cache with TTL similar to usage stats. Use in pair selection to prioritize under-compared pairs.

**Effort**: Low
**Impact**: High — enables proper prioritization and uncertainty-aware selection

---

### 9. Fix Usage Stats to Count Votes, Not Translations [M1]

`get_model_usage_stats()` at `app/services/stats_service.py:237` counts total translations generated. Change to count translations that have received at least one vote, so the selection algorithm prioritizes models that need more *rating data*.

**Effort**: Low
**Impact**: Medium — correct prioritization of under-rated models

---

### 10. Cost-Aware Model Selection [M3]

**Cost tiers** (based on output_cost_per_mtok):
- **Cheap**: <= $3/Mtok (DeepSeek, Gemini 3.1 Flash Lite, Gemini 2.5 Flash, Gemini 3 Flash)
- **Mid**: $3-$10/Mtok (Gemini 3.6 Flash, Gemini 3.5 Flash, Gemini 2.5 Pro)
- **Expensive**: > $10/Mtok (Gemini 3.1 Pro, GPT-5.6 Terra, Claude Opus 4.5/4.6, GPT-5.6 Sol)

**Constraint**: Max 2 expensive base model groups per session. After existing usage-based selection, if > 2 expensive groups selected, swap lowest-priority expensive group for highest-priority cheap/mid group.

**Effort**: Medium
**Impact**: Medium — cost savings, prevents all-expensive sessions

---

### 11. Query Difficulty via Model-Adjusted Residuals [Q2]

Track difficulty using residuals — how much each model underperforms its own baseline:

```python
residual = actual_rating - model_global_avg_rating
query_difficulty = -mean(residuals for all votes on this query)
```

**Tiers**:
- **Easy**: avg residual >= +0.3 (models consistently beat their baseline)
- **Hard**: avg residual <= -0.3 (models consistently underperform)
- **Medium**: in between
- **Unknown**: < 3 votes or < 2 different models -> conservative default

**Effort**: Medium
**Impact**: Medium — enables difficulty-aware query selection, smarter tie handling

---

### 12. Stratified Query Selection [Q1]

Replace pure random with stratified sampling:

```python
# Target per session: 2 easy, 5 medium, 2 hard, 1 unknown
# Backfill from remaining pool if any tier is exhausted
targets = {'easy': 2, 'medium': 5, 'hard': 2, 'unknown': 1}
selected = []
remaining = []
for tier, count in targets.items():
    pool = tier_pools[tier]  # pre-categorized query lists
    take = min(count, len(pool))
    selected.extend(random.sample(pool, take))
    # If tier was exhausted, add shortfall to remaining
    if take < count:
        remaining.extend(random.sample(pool, 0))  # nothing left in this tier
    else:
        remaining.extend(pool)  # leftover queries in this tier

# Backfill to reach 10 total from remaining across all tiers
shortfall = 10 - len(selected)
if shortfall > 0 and remaining:
    # Use all remaining queries not already selected
    available = [q for q in remaining if q not in selected]
    selected.extend(random.sample(available, min(shortfall, len(available))))

random.shuffle(selected)
```

Early in deployment, most queries will be 'unknown' — the backfill ensures 10 queries are always selected. Tests must not require every tier to be present when a tier is empty.

**Query-model cost coupling**: If session has 2 expensive groups, prefer hard queries. If all cheap models, lean toward easy/medium.

**Effort**: Medium
**Impact**: Medium — better discrimination, cost optimization

---

### 13. Confidence-Weighted Leaderboard Blend

Replace fixed 40/60 blend with RD-aware confidence weighting:

```python
confidence = 1 - (rd / 350)  # RD=350 -> 0.0, RD=80 -> 0.77
combined = normalized_glicko * confidence + normalized_avg_score * (1 - confidence)
```

This is a proper convex blend: weights always sum to 1.0. When RD is high (uncertain, confidence near 0), star ratings dominate. When RD is low (confident, confidence near 0.77), Glicko-2 dominates. System automatically shifts to the more reliable signal.

**Effort**: Low
**Impact**: Medium — smoother leaderboard during calibration, converges to Glicko-2 over time

---

### 14. Rebuild Function

Write `rebuild_ratings_from_comparisons()` to reconstruct Glicko-2 ratings from raw `PairwiseComparison` data. Wipe `ModelELO`, replay all comparisons through Glicko-2, restore ratings.

**Rebuild semantics**:
- Process comparisons in stable order: `created_at` ascending, then `id` ascending
- Run inside a single atomic transaction (rollback on any error)
- Wipe `ModelELO` rows, re-create with default rating=1500, RD=350, vol=0.06
- Replay each comparison through Glicko-2 update
- Regression test: incremental state (ratings after each comparison processed live) must match rebuilt state (ratings after full replay)

**Effort**: Low
**Impact**: Medium — enables safe experimentation, rollback capability

---

## Not Implementing

| Item | Reason |
|---|---|
| Adaptive K-factor (phased approach) | Glicko-2 handles this natively; adaptive K would be throwaway work |
| User reliability scoring (E4) | Single user (~90% of votes); no population to compare against |
| Make A/B pairwise the primary mode | Star ratings are the main data source; they provide class grouping, multi-model coverage, and absolute quality signal |
| Reduce star rating model count below 6 | 6 is the default, 10 is the hard limit; lower numbers prevent cross-family comparisons since model selection groups presets |
| Batch rating periods | Process immediately with MIN_RD=80 floor; simpler code, instant feedback, floor compensates for faster RD decay |
| M2: ELO-aware main-arena model selection | Deferred — current usage-based selection is adequate; ELO-awareness adds complexity for marginal gain with 12 base model groups |
| Q3: Query coverage tracking | Deferred — stratified sampling by difficulty provides sufficient coverage; explicit tracking adds state management overhead |

---

## Implementation Checklist

### Phase 1: Glicko-2 Migration (Medium Effort, High Impact)

- [x] **Glicko-2 core**: Implement Glicko-2 update algorithm in `elo_service.py`
  - Replace `update_ratings()` and `record_tie()` with Glicko-2 equivalents
  - Add `rating_deviation`, `volatility`, `legacy_elo_rating` columns to `ModelELO`
  - Parameters: tau=0.5, MIN_RD=80, c~48.6/week, initial RD=350, vol=0.06
  - Time-based RD increase for dormant models (track `last_comparison_at` per model)
  - Stable replay order: `created_at` ascending, then `id` ascending
  - Idempotent startup migration in `init_db.py` (check column existence, ALTER TABLE if missing)
  - Migration: copy current `elo_rating` to `legacy_elo_rating`, set RD=350, vol=0.06
  - Test: verify convergence behavior, RD decay, time-based increase
  - Test: regression test — rebuild matches incremental processing

- [x] **Score column**: Add `score` column to `PairwiseComparison`
  - Store fractional score per comparison
  - Backfill existing rows by outcome type: non-null winner/loser -> 1.0, null winner/loser with translations -> 0.5
  - Test: verify scores stored correctly for derived and explicit comparisons
  - Test: verify backfilled ties get 0.5, not 1.0

- [x] **Fractional scores**: Implement gap-based scoring in `vote_service.py`
  - Add score calculation: gap=4->1.0 (3 vs -1), gap=3->0.95 (2 vs -1), gap=2->0.85 (3 vs 1, 1 vs -1), gap=1->0.70 (3 vs 2, 2 vs 1)
  - Pass score through to `record_comparison()`
  - Test: verify 3 star vs -1 star produces larger rating shift than 2 star vs 1 star

- [x] **Tie logic update**: Update tie handling in `vote_service.py`
  - Skip both 3 star (until difficulty tracking)
  - Skip both -1 star
  - Tie (0.5) for both 1 star and both 2 star
  - Test: verify no comparison recorded for both-trash or both-perfect pairs

- [x] **Rebuild function**: Write `rebuild_ratings_from_comparisons()` in `elo_service.py`
  - Wipe `ModelELO`, replay all `PairwiseComparison` records through Glicko-2
  - Process in stable order: `created_at` ascending, then `id` ascending
  - Run inside atomic transaction
  - Test: regression test — rebuilt ratings must match incremental processing

### Phase 2: Pair Selection Improvements (Medium Effort, High Impact)

- [x] **Quick Compare filter**: Filter pairs in `get_random_comparison()`
  - Join with Vote table twice (aliased), constrained to **current user's** ratings only
  - Filter: both ratings >= 2, gap < 2
  - Test: verify only high-quality, close pairs shown
  - Test: verify ratings from other users do not affect pair eligibility

- [x] **Pair counts**: Track pair-level comparison counts
  - Count **explicit comparisons only** (source='explicit') per model pair
  - Use translation model names via joins, not winner/loser columns (ties have NULL winner/loser)
  - Cache with TTL
  - Test: verify counts match actual explicit comparison records
  - Test: verify ties are counted correctly (not collapsed into NULL group)

- [x] **Pair priority**: Replace ELO-diff sort with composite priority score
  - **Remove the random `limit(100)` batch** — fetch all uncompared pairs for the user, then apply priority scoring to the full set [P2]
  - Incorporate: ELO closeness (30%), RD uncertainty (25%), pair hunger (25%), same-rated bonus (+0.3)
  - Take top 5 by priority, pick one randomly
  - Test: verify under-compared, high-uncertainty, close-ELO pairs get priority
  - Test: verify best global pair is reachable (not filtered out by random batch)

### Phase 3: Query & Cost Optimization (Medium Effort, Medium Impact)

- [x] **Query difficulty**: Compute model-adjusted residuals per query
  - Calculate `residual = actual_rating - model_global_avg` per vote
  - Average residuals per query, categorize: easy/hard/medium/unknown
  - Requires >= 3 votes from >= 2 models for classification
  - Cache with TTL
  - Test: verify categorization matches expected difficulty

- [x] **Stratified query selection**: Replace random shuffle in `index()`
  - Target: 2 easy, 5 medium, 2 hard, 1 unknown per session
  - Backfill from remaining pool if any tier is exhausted (ensure 10 total)
  - ~~Couple with cost-aware model selection~~ (deferred — selections are currently independent)
  - Test: verify session includes queries from each tier when available
  - Test: verify 10 queries returned even when some tiers are empty

- [x] **Cost-aware model selection**: Add cost constraint to `_select_models()`
  - Tier models by output_cost_per_mtok: cheap (<=$3), mid ($3-$10), expensive (>$10)
  - Max 2 expensive base model groups per session
  - Swap if exceeded
  - Test: verify cost distribution across selected models

- [x] **Usage stats fix**: Count voted translations in `stats_service.py`
  - Change `get_model_usage_stats()` to join with Votes table
  - Count distinct translations with >= 1 vote per model
  - Test: verify model with 50 translations but 2 votes shows low usage

### Phase 4: Leaderboard & Polish (Low-Medium Effort, Medium Impact)

- [x] **Confidence-weighted blend**: Update `calculate_model_scores()`
  - Replace fixed 40/60 blend with convex RD-aware weighting
  - `combined = normalized_glicko * confidence + normalized_avg_score * (1 - confidence)` where `confidence = 1 - (rd / 350)`
  - Weights always sum to 1.0 (proper convex blend)
  - Test: verify high-RD models show star-driven scores, low-RD models show Glicko-driven scores
  - Test: verify combined score is always in [0, 1] range

- [x] **3-star tie refinement**: Once difficulty tracking is live
  - Skip 3-star/3-star ties only on easy queries (avg residual >= +0.3)
  - Record 3-star/3-star as tie (0.5) on medium/hard queries
  - Test: verify 3-star/3-star on hard queries produces tie, on easy queries produces nothing

- [~] **Dashboard metrics** (partially complete)
  - [x] Show model uncertainty (RD) on leaderboard
  - [ ] Show pair coverage heatmap (which model pairs need more comparisons)
  - [ ] Show query difficulty distribution
  - [ ] Show legacy ELO alongside Glicko-2 for comparison

---

## Dependency Graph

```
Glicko-2 core --> Fractional scores --> Tie logic update --> Phase 4 (Polish)
         --> Score column --> Rebuild function ----------------> |
                                                                 |
Quick Compare filter --> Pair counts --> Pair priority --------> |
                                                                 |
Query difficulty --> Stratified selection ----------------------> |
                 --> 3-star tie refinement ----------------------> |
                                                                 |
Cost-aware selection --------------------------------------------> |
Usage stats fix ------------------------------------------------> |
Confidence-weighted blend --> depends on Glicko-2 ---------------> 
```

Items within the same phase can be done in parallel. Items across phases have dependencies as shown.

---

## ADRs

The following architectural decisions are documented as ADRs:

- `docs/adr/0001-glicko-2-replaces-elo.md` — Replacing ELO with Glicko-2 (hard to reverse, fundamental system change)
- `docs/adr/0002-fractional-scores-for-derived-comparisons.md` — Gap-based fractional scoring (trade-off: information density vs noise)
- `docs/adr/0003-single-user-design-constraints.md` — Designing for a single-user system (shapes multiple decisions)
