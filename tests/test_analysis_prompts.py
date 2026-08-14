"""Regression tests for the copyable AI analysis prompt response formats."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _read_project_file(relative_path: str) -> str:
    return (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")


def test_multi_translation_prompt_requests_ratings_in_original_order() -> None:
    source = _read_project_file("static/js/main.js")

    ratings_heading = "**Ratings (Original Order)**"
    rankings_heading = "**Rankings (Best to Worst)**"

    assert ratings_heading in source
    assert "Option 1, Option 2, and so on" in source
    assert "Do not reorder this list by quality" in source
    assert "Option N — Model: Rating — brief rationale" in source
    assert source.index(ratings_heading) < source.index(rankings_heading)


def test_pairwise_prompt_requests_a_then_b_ratings() -> None:
    source = _read_project_file("static/js/compare.js")

    ratings_heading = "### Ratings (Original Order)"
    verdict_heading = "### Verdict"
    translation_a_rating = "- **Translation A**:"
    translation_b_rating = "- **Translation B**:"

    assert ratings_heading in source
    assert "Translation A first, then Translation B" in source
    assert "Do not reorder the ratings by quality" in source
    assert source.index(ratings_heading) < source.index(verdict_heading)
    assert source.index(translation_a_rating) < source.index(translation_b_rating)
