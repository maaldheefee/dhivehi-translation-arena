"""Pure model acquisition policy for short, sporadic evaluation bursts."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelCandidate:
    key: str
    base_model: str
    usage: int
    rating_deviation: float
    output_cost: float


def select_burst_models(
    candidates: list[ModelCandidate],
    max_models: int,
    expensive_threshold: float,
    max_expensive_groups: int,
    anchor_count: int = 2,
) -> list[str]:
    """Choose uncertain targets, then low-RD anchors, under a cost constraint."""
    if max_models <= 0:
        return []
    anchor_count = min(anchor_count, max(0, max_models - 1))
    target_count = max_models - anchor_count

    # High uncertainty and sparse usage indicate high information value.
    targets = sorted(
        candidates,
        key=lambda item: (item.rating_deviation, 1.0 / (item.usage + 1), -item.output_cost, item.key),
        reverse=True,
    )
    anchors = sorted(candidates, key=lambda item: (item.rating_deviation, -item.usage, item.output_cost, item.key))

    selected: list[ModelCandidate] = []
    expensive_bases: set[str] = set()

    def can_add(candidate: ModelCandidate) -> bool:
        if candidate in selected:
            return False
        if candidate.output_cost <= expensive_threshold or candidate.base_model in expensive_bases:
            return True
        return len(expensive_bases) < max_expensive_groups

    def add_from(pool: list[ModelCandidate], count: int, avoid_selected_bases: bool = False) -> None:
        for candidate in pool:
            if len(selected) >= max_models or count <= 0:
                break
            if avoid_selected_bases and any(item.base_model == candidate.base_model for item in selected):
                continue
            if not can_add(candidate):
                continue
            selected.append(candidate)
            if candidate.output_cost > expensive_threshold:
                expensive_bases.add(candidate.base_model)
            count -= 1

    add_from(targets, target_count)
    add_from(anchors, anchor_count, avoid_selected_bases=True)
    add_from(anchors, max_models - len(selected))
    return [candidate.key for candidate in selected]
