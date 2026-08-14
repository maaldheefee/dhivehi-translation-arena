from app.services.acquisition_policy import (
    ModelCandidate,
    QueryCandidate,
    select_burst_models,
    select_evaluation_session,
)


def candidate(key, rd, usage, cost=1.0, base=None):
    return ModelCandidate(key, base or key, usage, rd, cost)


def test_burst_selection_combines_new_targets_with_trusted_anchors():
    selected = select_burst_models(
        [
            candidate("new-a", 350, 0),
            candidate("new-b", 340, 1),
            candidate("middle", 180, 12),
            candidate("anchor-a", 80, 100),
            candidate("anchor-b", 90, 80),
        ],
        max_models=4,
        expensive_threshold=10,
        max_expensive_groups=2,
    )

    assert set(selected[:2]) == {"new-a", "new-b"}
    assert set(selected[2:]) == {"anchor-a", "anchor-b"}


def test_burst_selection_caps_expensive_base_families():
    selected = select_burst_models(
        [
            candidate("expensive-a", 350, 0, cost=20, base="family-a"),
            candidate("expensive-b", 340, 0, cost=20, base="family-b"),
            candidate("cheap-target", 330, 0, cost=1),
            candidate("anchor", 80, 100, cost=1),
        ],
        max_models=3,
        expensive_threshold=10,
        max_expensive_groups=1,
        anchor_count=1,
    )

    assert "anchor" in selected
    assert "cheap-target" in selected
    assert len({key for key in selected if key.startswith("expensive")}) == 1


def test_evaluation_session_fills_missing_target_query_cells_before_repeating_coverage():
    session = select_evaluation_session(
        models=[
            candidate("target", 350, 0),
            candidate("anchor", 80, 100),
        ],
        queries=[
            QueryCandidate(
                key="missing",
                text="missing target coverage",
                difficulty="medium",
                rated_models=frozenset({"anchor"}),
                discrimination=0.2,
            ),
            QueryCandidate(
                key="repeated",
                text="already covered",
                difficulty="medium",
                rated_models=frozenset({"target", "anchor"}),
                discrimination=1.0,
            ),
        ],
        max_models=2,
        max_queries=1,
        expensive_threshold=10,
        max_expensive_groups=2,
        anchor_count=1,
    )

    assert session.model_keys == ("target", "anchor")
    assert session.query_keys == ("missing",)


def test_evaluation_session_uses_discrimination_after_missing_coverage():
    session = select_evaluation_session(
        models=[candidate("target", 350, 0), candidate("anchor", 80, 100)],
        queries=[
            QueryCandidate("weak", "weak", "medium", frozenset(), 0.1),
            QueryCandidate("strong", "strong", "medium", frozenset(), 0.9),
        ],
        max_models=2,
        max_queries=1,
        expensive_threshold=10,
        max_expensive_groups=2,
        anchor_count=1,
    )

    assert session.query_keys == ("strong",)


def test_evaluation_session_retains_difficulty_diversity_among_equally_missing_queries():
    session = select_evaluation_session(
        models=[candidate("target", 350, 0), candidate("anchor", 80, 100)],
        queries=[
            QueryCandidate("hard-best", "hard best", "hard", frozenset(), 0.9),
            QueryCandidate("hard-next", "hard next", "hard", frozenset(), 0.8),
            QueryCandidate("easy", "easy", "easy", frozenset(), 0.7),
        ],
        max_models=2,
        max_queries=2,
        expensive_threshold=10,
        max_expensive_groups=2,
        anchor_count=1,
    )

    assert session.query_keys == ("hard-best", "easy")


def test_evaluation_session_prefers_lower_cost_query_when_information_value_matches():
    session = select_evaluation_session(
        models=[candidate("target", 350, 0, cost=5), candidate("anchor", 80, 100, cost=5)],
        queries=[
            QueryCandidate("long", "long", "medium", frozenset(), 0.5, estimated_tokens=500),
            QueryCandidate("short", "short", "medium", frozenset(), 0.5, estimated_tokens=50),
        ],
        max_models=2,
        max_queries=1,
        expensive_threshold=10,
        max_expensive_groups=2,
        anchor_count=1,
    )

    assert session.query_keys == ("short",)


def test_evaluation_session_reserves_a_bounded_deterministic_exploration_slot():
    session = select_evaluation_session(
        models=[candidate("target", 350, 0), candidate("anchor", 80, 100)],
        queries=[
            *[
                QueryCandidate(
                    f"known-{index}",
                    f"known {index}",
                    "medium",
                    frozenset(),
                    1.0 - index / 10,
                    observation_count=10,
                )
                for index in range(5)
            ],
            QueryCandidate("explore-a", "explore a", "unknown", frozenset(), 0.0),
            QueryCandidate("explore-b", "explore b", "unknown", frozenset(), 0.0),
        ],
        max_models=2,
        max_queries=5,
        expensive_threshold=10,
        max_expensive_groups=2,
        anchor_count=1,
        exploration_share=0.2,
        exploration_seed=7,
    )

    explored = {"explore-a", "explore-b"}.intersection(session.query_keys)
    assert len(explored) == 1
    assert session == select_evaluation_session(
        models=[candidate("target", 350, 0), candidate("anchor", 80, 100)],
        queries=[
            *[
                QueryCandidate(
                    f"known-{index}",
                    f"known {index}",
                    "medium",
                    frozenset(),
                    1.0 - index / 10,
                    observation_count=10,
                )
                for index in range(5)
            ],
            QueryCandidate("explore-a", "explore a", "unknown", frozenset(), 0.0),
            QueryCandidate("explore-b", "explore b", "unknown", frozenset(), 0.0),
        ],
        max_models=2,
        max_queries=5,
        expensive_threshold=10,
        max_expensive_groups=2,
        anchor_count=1,
        exploration_share=0.2,
        exploration_seed=7,
    )


def test_evaluation_session_fills_query_limit_when_all_queries_are_unobserved():
    session = select_evaluation_session(
        models=[candidate("target", 350, 0), candidate("anchor", 80, 100)],
        queries=[QueryCandidate(str(index), str(index), "unknown", frozenset(), 0.0) for index in range(12)],
        max_models=2,
        max_queries=10,
        expensive_threshold=10,
        max_expensive_groups=2,
        anchor_count=1,
    )

    assert len(session.query_keys) == 10
