"""Pure model acquisition policy for short, sporadic evaluation bursts."""

import random
from dataclasses import dataclass


@dataclass(frozen=True)
class ModelCandidate:
    key: str
    base_model: str
    usage: int
    rating_deviation: float
    output_cost: float


@dataclass(frozen=True)
class QueryCandidate:
    key: str
    text: str
    difficulty: str
    rated_models: frozenset[str]
    discrimination: float
    estimated_tokens: int = 1
    observation_count: int = 0


@dataclass(frozen=True)
class EvaluationSession:
    model_keys: tuple[str, ...]
    query_keys: tuple[str, ...]


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


def select_evaluation_session(
    models: list[ModelCandidate],
    queries: list[QueryCandidate],
    max_models: int,
    max_queries: int,
    expensive_threshold: float,
    max_expensive_groups: int,
    anchor_count: int = 2,
    exploration_share: float = 0.1,
    exploration_seed: int = 0,
) -> EvaluationSession:
    """Choose the models and Queries that yield the most useful next ballot evidence."""
    model_keys = select_burst_models(
        models,
        max_models,
        expensive_threshold,
        max_expensive_groups,
        anchor_count,
    )
    target_count = max(0, len(model_keys) - min(anchor_count, max(0, len(model_keys) - 1)))
    target_keys = frozenset(model_keys[:target_count])
    selected_model_cost = sum(model.output_cost for model in models if model.key in model_keys)
    exploration_count = min(max_queries, max(0, int(max_queries * exploration_share)))
    exploration: list[QueryCandidate] = []
    exploration_pool: list[QueryCandidate] = []
    if exploration_count and queries:
        least_observed = min(query.observation_count for query in queries)
        exploration_pool = sorted(
            (query for query in queries if query.observation_count == least_observed),
            key=lambda query: query.key,
        )
        randomizer = random.Random(exploration_seed)  # noqa: S311 - deterministic policy exploration, not security
        exploration = randomizer.sample(exploration_pool, min(exploration_count, len(exploration_pool)))

    remaining = [query for query in queries if query not in exploration_pool]
    exploitation_limit = max_queries - len(exploration)
    if len(remaining) < exploitation_limit:
        fallback = [query for query in exploration_pool if query not in exploration]
        remaining.extend(fallback[: exploitation_limit - len(remaining)])
    selected_queries: list[QueryCandidate] = []
    selected_difficulties: set[str] = set()
    while remaining and len(selected_queries) < exploitation_limit:
        best = min(
            remaining,
            key=lambda query: (
                -len(target_keys - query.rated_models),
                query.difficulty in selected_difficulties,
                -query.discrimination,
                query.estimated_tokens * selected_model_cost,
                query.key,
            ),
        )
        selected_queries.append(best)
        selected_difficulties.add(best.difficulty)
        remaining.remove(best)
    selected_queries.extend(exploration)
    return EvaluationSession(tuple(model_keys), tuple(query.key for query in selected_queries))
