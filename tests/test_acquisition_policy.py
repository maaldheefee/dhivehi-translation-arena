from app.services.acquisition_policy import ModelCandidate, select_burst_models


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
