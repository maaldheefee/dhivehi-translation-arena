# Voting Systems: Technical Documentation

This document details the voting systems used in the Dhivehi Translation Arena, their trade-offs, and our implementation approach.

## Table of Contents

1. [Current Implementation](#current-implementation)
2. [Our Constraints](#our-constraints)
3. [Voting Method Analysis](#voting-method-analysis)
4. [Recommended Hybrid Approach](#recommended-hybrid-approach)
5. [Implementation Details](#implementation-details)

---

## Current Implementation

### Star Rating System

We use a 4-tier star rating where users rate each translation independently:

| Rating | Label     | Score Impact |
|--------|-----------|--------------|
| ⭐⭐⭐   | Excellent | +3 points    |
| ⭐⭐     | Good      | +1 point     |
| ⭐       | Okay      | 0 points     |
| 🗑️      | Rejected  | -2 points    |

### Current Scoring Formula

```python
average_score = total_score / votes_cast
```

Where `total_score` is the sum of all rating impacts for a model.

### Current Leaderboard

Models are ranked by `average_score` (descending), with additional metrics:
- **Bang for Buck**: Score per dollar spent
- **Projected Cost**: Extrapolated cost per 100k words
- **Rating Distribution**: Visual breakdown of votes

### Limitations of Current System

1. **No relative comparison**: Rating A as 2★ and B as 2★ tells us nothing about A vs B preference
2. **Absolute scale ambiguity**: "Good" means different things on different days
3. **No tie handling**: When two translations seem equally good, forced to pick arbitrary ratings
4. **Sparse data problem**: With few voters, averages are noisy

---

## Our Constraints

| Constraint | Impact |
|------------|--------|
| **1-2 voters** | Can't rely on wisdom of crowds; need robust single-voter signals |
| **Low data volume** | Statistical methods need high K-factor / fast convergence |
| **Cost-conscious** | Must reuse existing translations, not generate new ones |
| **Cognitive load** | Sorting 6 items is hard; pairwise or small groups better |

---

## Voting Method Analysis

### Method 1: Star Ratings (Current)

**How it works**: Rate each translation on absolute scale (1-3 stars or reject).

**Pros**:
- Simple UI, fast voting
- Captures sentiment about individual translations
- Already implemented

**Cons**:
- Doesn't capture relative preferences
- "2-star" calibration drifts over time
- Can't express ties explicitly

**Statistical properties**:
- Requires ~30+ votes per model for stable averages
- Subject to voter calibration drift

---

### Method 2: Pairwise Comparison (ELO/Bradley-Terry)

**How it works**: Show 2 translations, ask "which is better?"

**Underlying model**: Bradley-Terry assumes probability of A beating B is:

```
P(A > B) = 1 / (1 + 10^((R_B - R_A) / 400))
```

Where `R_A` and `R_B` are ELO ratings.

**ELO Update Formula**:
```python
K = 32  # Higher = faster convergence, more volatile
expected = 1 / (1 + 10**((loser_elo - winner_elo) / 400))
winner_elo += K * (1 - expected)
loser_elo += K * (0 - (1 - expected))
```

**Pros**:
- Very quick to vote (binary choice)
- No absolute calibration needed
- Proven at scale (Chess, Chatbot Arena)
- Handles ties naturally

**Cons**:
- Need many comparisons: O(n²) pairs for n models
- With 6 models: C(6,2) = 15 unique pairs per source text
- Can be tedious if shown many pairs

**Statistical properties**:
- Converges with ~50 comparisons per model
- Self-correcting: bad ratings get overwritten

**Key insight for us**: We can derive pairwise data from existing star ratings:
- If A=3★ and B=1★ on same query → A wins
- If A=2★ and B=2★ → Tie (or skip)

---

### Method 3: Ranking / Sorting

**How it works**: Show N translations, order from best to worst.

**Pros**:
- Rich signal: ordering 4 items gives C(4,2) = 6 pairwise comparisons
- Single action instead of multiple votes
- Very intuitive

**Cons**:
- 6+ items causes cognitive overload
- 3-4 items is optimal
- UI implementation more complex (drag-and-drop)

**Key insight for us**: 
- For 4 items: 1 ranking action = 6 pairwise signals
- For 3 items: 1 ranking action = 3 pairwise signals

---

### Method 4: Best-of-N Selection

**How it works**: Show N translations, click the best one.

**Pros**:
- Simplest UI possible
- Very fast voting
- Clear signal for top performer

**Cons**:
- Only identifies winner, not relative ordering of losers
- If A > B ≈ C ≈ D, we only learn A is best

---

### Method 5: Hybrid Multi-Signal

**How it works**: Combine multiple voting methods:
1. Primary: Star ratings (captures absolute quality)
2. Secondary: Pairwise/ranking (captures relative preference)
3. Derived: Infer pairwise from star ratings when possible

**Composite scoring options**:
```python
# Option A: Weighted average
composite = 0.6 * normalized_star_score + 0.4 * normalized_elo

# Option B: Rank aggregation (Borda count)
borda = avg_rank_by_stars + avg_rank_by_elo

# Option C: Multiple leaderboards
# Let users see different perspectives
```

**Pros**:
- Robust with low data
- Multiple perspectives on quality
- Can add voting modes incrementally

**Cons**:
- More complex implementation
- Users may be confused by multiple scores

---

## Recommended Hybrid Approach

Given our constraints, we recommend:

### Phase 1: Derive Pairwise from Existing Data

No new UI needed. Simply compute implicit pairwise comparisons:

```python
for query in queries_with_votes:
    translations = query.translations
    for t1, t2 in combinations(translations, 2):
        v1 = get_vote(t1)  # e.g., 3
        v2 = get_vote(t2)  # e.g., 1
        if v1 > v2:
            record_comparison(winner=t1.model, loser=t2.model)
        elif v2 > v1:
            record_comparison(winner=t2.model, loser=t1.model)
        # equal ratings = tie, skip or record as draw
```

### Phase 2: Add "Quick Compare" Mode

New voting mode for explicit pairwise:

1. Show 2-3 previously generated translations (same source text)
2. User clicks best one (or "tie")
3. Store result in new `pairwise_comparisons` table
4. Update ELO ratings

**Key benefit**: Zero API cost - reuses existing translations.

### Phase 3: Multi-Leaderboard Display

Show multiple ranking perspectives:

| Model     | Avg Rating | ELO  | Win Rate |
|-----------|------------|------|----------|
| Claude    | 2.45       | 1580 | 67%      |
| GPT-4     | 2.30       | 1520 | 58%      |
| Gemini    | 2.10       | 1490 | 52%      |

---

## Implementation Details

### New Database Models

```python
class PairwiseComparison(Base):
    __tablename__ = "pairwise_comparisons"
    
    id = Column(Integer, primary_key=True)
    query_id = Column(Integer, ForeignKey("queries.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    winner_model = Column(String(50), nullable=True)  # NULL = tie
    loser_model = Column(String(50), nullable=True)
    # For explicit comparisons, store translation IDs
    translation_a_id = Column(Integer, ForeignKey("translations.id"))
    translation_b_id = Column(Integer, ForeignKey("translations.id"))
    source = Column(String(20))  # 'derived' or 'explicit'
    created_at = Column(DateTime, default=func.now())

class ModelELO(Base):
    __tablename__ = "model_elo"
    
    id = Column(Integer, primary_key=True)
    model = Column(String(50), nullable=False, unique=True)
    elo_rating = Column(Float, default=1500.0)
    wins = Column(Integer, default=0)
    losses = Column(Integer, default=0)
    ties = Column(Integer, default=0)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
```

### ELO Service

```python
class ELOService:
    K_FACTOR = 32  # High for fast convergence with low data
    DEFAULT_ELO = 1500.0
    
    def update_ratings(self, winner: str, loser: str):
        winner_elo = self.get_or_create(winner)
        loser_elo = self.get_or_create(loser)
        
        expected_winner = 1 / (1 + 10**((loser_elo.elo_rating - winner_elo.elo_rating) / 400))
        expected_loser = 1 - expected_winner
        
        winner_elo.elo_rating += self.K_FACTOR * (1 - expected_winner)
        loser_elo.elo_rating += self.K_FACTOR * (0 - expected_loser)
        
        winner_elo.wins += 1
        loser_elo.losses += 1
    
    def record_tie(self, model_a: str, model_b: str):
        # Ties pull ratings toward each other
        a_elo = self.get_or_create(model_a)
        b_elo = self.get_or_create(model_b)
        
        expected_a = 1 / (1 + 10**((b_elo.elo_rating - a_elo.elo_rating) / 400))
        
        a_elo.elo_rating += self.K_FACTOR * (0.5 - expected_a)
        b_elo.elo_rating += self.K_FACTOR * (0.5 - (1 - expected_a))
        
        a_elo.ties += 1
        b_elo.ties += 1
```

### Quick Compare API Endpoints

```python
@main_bp.route("/compare/random")
def get_random_comparison():
    """Get 2-3 translations for the same query to compare."""
    # Find queries with multiple translations that haven't been compared
    # Prioritize models with similar ELO (most informative comparisons)
    pass

@main_bp.route("/compare/submit", methods=["POST"])
def submit_comparison():
    """Record a pairwise comparison result."""
    data = request.json
    winner_id = data.get("winner")  # translation ID or None for tie
    translation_ids = data.get("translations")  # [id1, id2] or [id1, id2, id3]
    pass
```

### Leaderboard Updates

Add ELO and win rate to stats page:

```python
def get_combined_leaderboard():
    star_scores = calculate_model_scores()  # existing
    elo_scores = get_all_elo_ratings()      # new
    
    combined = []
    for model in all_models:
        combined.append({
            "model": model,
            "avg_rating": star_scores.get(model, {}).get("average_score", 0),
            "elo": elo_scores.get(model, 1500),
            "win_rate": calculate_win_rate(model),
        })
    
    return combined
```

---

## Migration Strategy

1. **Derive initial pairwise data** from existing star ratings (one-time script)
2. **Calculate initial ELO** from derived pairwise data
3. **Deploy** new Quick Compare mode
4. **Running updates**: Both star ratings and explicit comparisons update ELO

---

## References

- [Bradley-Terry Model](https://en.wikipedia.org/wiki/Bradley%E2%80%93Terry_model)
- [Chatbot Arena](https://lmsys.org/blog/2023-05-03-arena/) - Uses ELO for LLM ranking
- [ELO Rating System](https://en.wikipedia.org/wiki/Elo_rating_system)
- [TrueSkill](https://www.microsoft.com/en-us/research/project/trueskill-ranking-system/) - Microsoft's Bayesian rating system
