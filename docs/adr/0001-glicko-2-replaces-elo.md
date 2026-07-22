# ADR 0001: Glicko-2 Replaces ELO

## Status

Accepted

## Date

2026-07-22

## Context

The Dhivehi Translation Arena uses an ELO rating system (K_FACTOR=32, default=1500) to rank translation models based on pairwise comparisons. Comparisons come from two sources: derived (inferred from star ratings) and explicit (direct A/B choices in Quick Compare).

Key constraints:
- **Single user**: ~90%+ of all votes come from one person. No cross-user consensus to average out bias.
- **Infrequent usage**: Bursts of activity when new models are released, then dormant for days or weeks.
- **Sparse data**: ~21 active models, each with limited comparisons.
- **Model drift risk**: LLM providers silently update models behind the same API endpoint.

The current ELO system has two fundamental problems:
1. **Fixed K-factor**: Over-reacts to outliers once ratings stabilize; under-converges when data is sparse.
2. **No uncertainty tracking**: A model at 1500 ± 50 is treated identically to one at 1500 ± 300. Pair selection can't prioritize comparisons that would reduce uncertainty.

An adaptive K-factor (tiered by match count) was considered as an intermediate step but rejected as throwaway work — it's a crude approximation of what Glicko-2 does continuously.

## Decision

Replace standard ELO with Glicko-2.

**Parameters**:
- System constant τ = 0.5 (moderate volatility)
- MIN_RD = 80 (floor to prevent overconfidence)
- Time-based RD increase: c ≈ 48.6/week
- Initial RD = 350.0, volatility = 0.06

**Processing model**: Each comparison processed immediately (no batching). MIN_RD floor compensates for faster RD decay from per-comparison processing.

**Migration**: Preserve existing `elo_rating` as starting Glicko-2 rating. Set RD=350 (max uncertainty). Copy current ratings to `legacy_elo_rating` column for rollback.

## Consequences

**Positive**:
- Uncertainty tracking (RD) enables smarter pair selection — prioritize comparisons that reduce uncertainty
- Automatic K-factor adaptation based on data volume and time since last game
- Time-based RD increase handles dormancy naturally — dormant models become more uncertain, new comparisons have more impact
- Confidence intervals on leaderboard
- Handles sparse data better than fixed-K ELO

**Negative**:
- Schema migration required (3 new columns on `ModelELO`)
- Three values per model instead of one (rating, RD, volatility) — harder to debug
- Per-comparison processing causes faster RD decay than batched; mitigated by MIN_RD=80 floor
- Glicko-2 algorithm is ~40 lines more complex than ELO update

**Neutral**:
- `legacy_elo_rating` column preserved for comparison and rollback; can be dropped after confidence is established
