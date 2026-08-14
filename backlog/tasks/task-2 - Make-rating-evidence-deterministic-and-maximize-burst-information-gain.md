---
id: TASK-2
title: Make rating evidence deterministic and maximize burst information gain
status: Done
assignee:
  - '@codex'
created_date: '2026-08-14 05:02'
updated_date: '2026-08-14 05:45'
labels:
  - ready-for-agent
dependencies: []
references:
  - CONTEXT.md
  - docs/adr/0001-glicko-2-replaces-elo.md
  - docs/adr/0002-fractional-scores-for-derived-comparisons.md
  - docs/adr/0003-single-user-design-constraints.md
  - 'https://glicko.net/glicko/glicko2.pdf'
priority: high
type: enhancement
ordinal: 2000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Problem Statement

The arena is used in short bursts to place newly released translation models quickly. A Rating Ballot currently expands into many sequential Glicko periods, so arbitrary pair order and repeated submission can change ratings. Derived rows mix mutable projections with Explicit Comparison events, dormancy is invisible until after the next comparison, and the leaderboard blends correlated star and Glicko evidence while ignoring star-sample uncertainty. Model, Query, and pair selection then optimize hand-tuned coverage heuristics against this unstable ranking instead of maximizing useful evidence per judgment.

## Solution

Create one deep rating-projection module that treats each immutable Rating Ballot as one simultaneous weighted period, treats each Explicit Comparison as one full-strength period, and rebuilds deterministically from raw evidence. Make Glicko rating plus effective RD the canonical relative ranking while retaining star distributions as the absolute-quality profile. Once ranking is stable, create one deep Evaluation Session selection module that prioritizes new targets, calibrated anchors, unrated target-query coverage, discriminating Queries, and cost.

## Decision Document

- Rating Ballots are immutable raw evidence.
- An identical ballot retry is a no-op; a conflicting retry is rejected.
- Exceptional correction is a maintenance operation and is not part of normal UI behavior.
- All Derived Comparisons from one ballot are evaluated simultaneously from the same pre-period state.
- Derived outcomes carry normalized evidence weights so increasing a ballot from four to six models does not create quadratic confidence.
- Fractional outcome strength and evidence weight are separate concepts.
- Explicit Comparisons remain immutable, full-strength rating periods.
- Existing rated Translations may act as anchors for newly rated models, but old evidence is not recreated or counted again.
- Raw Rating Ballots and Explicit Comparisons are the source of truth; Derived Comparisons and model ratings are projections.
- Rebuilding the same evidence with the same clock produces the same complete rating state.
- The preserved migration seed remains part of a rebuild and is never deleted accidentally.
- Effective RD is projected for the requested time before ranking or pair selection and is not persisted merely because a page is viewed.
- Glicko rating, RD, and volatility form the canonical relative rating state.
- The star average and distribution remain the canonical absolute-quality profile.
- The Confidence-Weighted Blend is retired rather than used as a canonical score.
- Default leaderboard ordering is conservative during sparse evidence; the raw Glicko estimate remains visible.
- Evaluation Sessions include new or uncertain target models and one or two low-RD anchors when available.
- Query acquisition prioritizes missing target coverage and historical discrimination while retaining difficulty diversity and respecting cost.
- Comparison recording owns same-Query, distinct-model, eligibility, uniqueness, and score invariants and commits once.

## Testing Decisions

Tests exercise module interfaces and observable invariants rather than private calculation steps. Rating-projection tests use controlled clocks and shuffled insertion orders. Submission tests cover duplicate retries, conflicts, partial failure, and atomicity. Statistical tests compare four-model and six-model ballots, Derived versus Explicit evidence, dormancy projection, rebuild equivalence, and sparse leaderboard behavior. Selection tests use small deterministic histories and assert anchor inclusion, missing-cell preference, cost limits, and exploration behavior. Existing Glicko regression tests and the repository test suite remain prior art and must stay green.

## Out of Scope

- Fresh-output generation and provider-version tracking.
- Background workers, queues, distributed caches, or distributed transactions.
- A full contextual-bandit or reinforcement-learning system.
- Multi-user reliability or inter-rater agreement scoring.
- A normal UI for changing historical star ratings.
- Replacing Glicko with TrueSkill, Bradley-Terry, or another ranking family.
- Redesigning the star rubric or its user-facing labels.

## Further Notes

The weighted Derived-evidence rule is a documented extension around the Glicko period calculation. Before rollout, historical replay should compare rank stability and RD contraction under candidate weights. Calibration may choose constants, but it must not change the settled semantics above.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Identical Rating Ballot retries leave votes, Derived Comparisons, timestamps, and complete model rating state unchanged
- [x] #2 A conflicting Rating Ballot retry is rejected without partial database changes
- [x] #3 All Derived outcomes from one Rating Ballot use the same pre-period model state and are invariant to pair and insertion order
- [x] #4 Derived evidence from larger ballots has bounded normalized confidence contribution rather than quadratic RD contraction
- [x] #5 Explicit Comparisons retain full-strength win, loss, and tie behavior
- [x] #6 Live updates, CLI rebuilds, and repeated projections produce the same rating state and preserve the durable initial seed
- [x] #7 Leaderboard and pair selection use effective dormancy-adjusted RD before a new comparison is submitted
- [x] #8 The leaderboard uses canonical Glicko state for relative ranking and presents star statistics separately without Confidence-Weighted Blend
- [x] #9 Invalid or duplicate Explicit Comparisons cannot be recorded and tie outcomes count correctly in progress statistics
- [x] #10 Evaluation Session selection includes calibrated anchors when available and prioritizes unrated target-query coverage and discriminating Queries within cost constraints
- [x] #11 Historical migration succeeds on the existing schema and all repository tests pass
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Characterize Evaluation Session behavior through the public acquisition-policy interface and route responses.
2. Extend the pure acquisition-policy module with Query candidates and an Evaluation Session result that selects uncertain targets plus calibrated anchors, then ranks Queries by missing target coverage, historical discrimination, difficulty diversity, cost proxy, and bounded exploration.
3. Add a database adapter in the main blueprint that constructs policy inputs from immutable vote/translation history, preserving manual model exclusions and requested model-count limits across both routes.
4. Replace the legacy stratified selector in index(), keep display-order randomization separate from policy choice, and remove superseded shallow selection logic.
5. Run deterministic scenario tests, route-level tests, the full suite, focused Ruff, and ty; then finalize TASK-2 only if criterion 10 is objectively satisfied.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Implemented commits 14fb6e6..b705f9e: deterministic clocks/snapshots; additive ballot schema and idempotent legacy backfill; immutable atomic ballot submission; normalized simultaneous weighted Glicko periods; explicit full-weight periods and validation; raw-evidence projection rebuild; CLI-only correction; effective read-time RD; conservative canonical leaderboard with separate stars; evidence-aware base-family display; and a tested burst model policy using uncertain targets, low-RD anchors, and cost caps. Verification: 84 tests pass; focused Ruff and ty checks pass. Acceptance criterion 10 remains open because query-level missing-cell and historical-discrimination acquisition has not yet replaced the existing stratified query selector.

Implemented the Evaluation Session policy and route integration for criterion 10. The pure policy now represents Query candidates and returns selected target/anchor models plus Queries, prioritizing missing target-query cells, difficulty diversity, historical rating discrimination, query/model cost proxy, and deterministic bounded exploration. Both index and get_available_models now use the same effective-RD-backed adapter; manual exclusions and requested count are covered at route level; the legacy random grouping and stratified query selector were removed. Verification: 92 tests pass (two known SQLite datetime-adapter warnings); focused Ruff and ty checks pass.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Completed deterministic rating evidence and burst information-gain work. Criterion 10 now uses one Evaluation Session policy for uncertain targets, low-RD anchors, missing target-query coverage, historical discrimination, difficulty diversity, cost, and bounded exploration across both arena routes. Objective verification: 92 repository tests passed; focused Ruff and ty checks passed; route tests cover rendered policy selections plus hidden exclusions and requested model counts. The two existing Python 3.14 SQLite datetime-adapter deprecation warnings remain non-failing.
<!-- SECTION:FINAL_SUMMARY:END -->
