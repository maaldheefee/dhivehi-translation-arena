# ADR 0003: Single-User Design Constraints

## Status

Accepted

## Date

2026-07-22

## Context

The Dhivehi Translation Arena is primarily used by a single developer (~90%+ of all votes). One or two other users may contribute very low volume. The tool is used infrequently — bursts of activity when new models are released, then dormant for days or weeks.

This is not a crowdsourced rating platform. It is a personal ranking tool. The "arena" framing (many users contributing comparisons that average out individual bias) does not apply.

## Decision

Design the system for a single-user reality. This shapes multiple decisions:

1. **Drop user reliability scoring (E4)**: Can't compute agreement rates with one user. No population to compare against. Replaced by Glicko-2's volatility parameter, which captures intra-rater consistency (does the user give the same model similar ratings across different queries?).

2. **Glicko-2 is even more justified**: With one user, there's no cross-user consensus to average out individual bias. The uncertainty tracking (RD) is critical — it tells the system how confident it can be in ratings derived from a single perspective.

3. **Time-based RD increase is essential**: Dormant periods of days/weeks mean models haven't been compared recently. RD creeps back up, so when the user returns, new comparisons have more impact. This handles both dormancy and potential provider-side model drift.

4. **MIN_RD=80 floor**: Prevents the system from becoming unresponsive after active sessions. Each comparison must still matter, even after many data points. With one user, the bottleneck is the user's time — every comparison must extract maximum information.

5. **Quick Compare filtering is aggressive**: Only show pairs where both translations are ≥ 2★ and gap < 2. The user's time is precious; don't waste it on obvious pairs or low-quality translations.

6. **Query difficulty via model-adjusted residuals**: Raw average star rating conflates query difficulty with model capability. If a query is only rated by cheap/weak models, it looks "hard" when it might just be the models. Residuals remove this confound — important when the single user may test different model subsets on different queries.

7. **Process immediately, no batching**: User wants instant feedback after submitting ratings. Batching rating periods adds complexity and delays gratification. MIN_RD floor compensates for the faster RD decay.

## Consequences

**Positive**:
- Simpler system: no user reliability scoring, no batch processing, no multi-user coordination
- Every design choice optimized for information extraction per unit of user effort
- Glicko-2's properties (RD, volatility, time-based decay) align perfectly with usage pattern

**Negative**:
- No cross-user validation — if the single user has systematic bias (e.g., always rates longer translations higher), it's embedded in all ratings
- System cannot detect if the user's rating standards drift over time (though Glicko-2 volatility partially captures this)
- If the tool ever needs to support many users, user reliability scoring and batch processing would need to be revisited

**Mitigation for bias risk**: The user can compare their ratings against external benchmarks (e.g., professional translator assessments) periodically. The `legacy_elo_rating` column provides a historical reference point.
