# ADR 0002: Fractional Scores for Derived Comparisons

## Status

Accepted

## Date

2026-07-22

## Context

Derived comparisons are inferred from star ratings: if Translation A gets 3★ and Translation B gets 1★, A wins over B. The current system treats all derived wins as binary (score=1.0 for winner, 0.0 for loser), regardless of the rating gap.

This means a 3★ vs -1★ comparison (4-level gap, "Excellent vs Trash") produces the same ELO update as a 2★ vs 1★ comparison (1-level gap, "Meaning Correct vs Understandable"). The 4-level gap is a confident, clear distinction; the 1-level gap is a marginal, subjective borderline.

With Glicko-2 replacing ELO, the system accepts fractional scores on [0, 1] (0.5 = tie, 1.0 = decisive win). This enables encoding gap-based confidence directly into the score.

## Decision

Map the star rating gap to a fractional Glicko-2 score:

```python
# Rating scale: 3, 2, 1, -1 (NOT 3, 2, 1, 0)
# Examples: 3 vs 2 -> gap 1, 3 vs 1 -> gap 2, 2 vs -1 -> gap 3, 3 vs -1 -> gap 4
gap = abs(r1 - r2)
if gap >= 4:    score = 1.0   # 3 vs -1, decisive
elif gap >= 3:  score = 0.95  # 2 vs -1, strong
elif gap >= 2:  score = 0.85  # 3 vs 1, or 1 vs -1, clear
else:           score = 0.70  # 3 vs 2, or 2 vs 1, marginal
```

Winner gets `score`, loser gets `1 - score`.

**Explicit A/B comparisons remain binary** (1.0/0.0/0.5). The act of choosing is the signal; fractional modulation would double-count the star rating signal already captured in derived comparisons.

**Gap=1 comparisons are not skipped.** With sparse data and a single user, every comparison counts. The 0.70 score already downweights marginal comparisons. Glicko-2's volatility parameter captures inconsistency over time.

## Alternatives Considered

1. **K-multiplier on ELO**: Apply a multiplier to K-factor based on gap. Rejected because Glicko-2 has no K-factor — updates are driven by RD and volatility.

2. **Skip gap=1 entirely**: Throw away ~50% of derived comparisons. Rejected as too aggressive for sparse data. The fractional score handles the noise concern.

3. **Infer confidence from context for explicit A/B**: Use star gap to modulate explicit comparison scores. Rejected — double-counts star signal and adds complexity.

## Consequences

**Positive**:
- Large-gap comparisons (3★ vs -1★) move ratings more than small-gap (2★ vs 1★)
- Glicko-2 naturally handles fractional scores — no algorithm modification needed
- Score stored in `PairwiseComparison.score` column for rebuild capability

**Negative**:
- Adds a `score` column to `PairwiseComparison` (schema change)
- Existing comparisons have NULL score (treated as 1.0 during rebuild)
