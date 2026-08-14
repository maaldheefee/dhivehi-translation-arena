from pathlib import Path

PROJECT_ROOT = Path(__file__).parents[1]


def test_mobile_navigation_has_accessible_controls():
    template = (PROJECT_ROOT / "templates" / "base.html").read_text()

    assert 'id="mobile-menu-toggle"' in template
    assert 'aria-controls="main-nav"' in template
    assert 'aria-expanded="false"' in template
    assert 'id="mobile-menu-backdrop"' in template


def test_mobile_navigation_behavior_is_wired_up():
    script = (PROJECT_ROOT / "static" / "js" / "main.js").read_text()

    assert 'setAttribute("aria-expanded", String(isOpen))' in script
    assert 'event.key === "Escape"' in script
    assert 'mobileMenuBackdrop?.addEventListener("click"' in script


def test_mobile_toggle_override_follows_desktop_default():
    stylesheet = (PROJECT_ROOT / "static" / "css" / "styles.css").read_text()
    desktop_default = stylesheet.rfind("/* Mobile menu toggle — hidden on desktop */")
    mobile_override = stylesheet.rfind("/* Kept after the desktop default")

    assert desktop_default > 0
    assert mobile_override > desktop_default


def test_rating_run_keeps_retries_and_votes_bound_to_one_query():
    script = (PROJECT_ROOT / "static" / "js" / "main.js").read_text()

    assert "const run = { sourceText: query, queryId: null, eventSource: null };" in script
    assert "if (activeRun !== run) return;" in script
    assert "retrySingle(run, modelKey)" in script
    assert "retrySingle(elements.queryInput.value" not in script
    assert "card.dataset.queryId === String(queryId)" in script


def test_comparison_exposes_manual_and_direct_ai_judging():
    template = (PROJECT_ROOT / "templates" / "compare.html").read_text()
    script = (PROJECT_ROOT / "static" / "js" / "compare.js").read_text()

    assert 'id="compare-ai-judge-btn"' in template
    assert 'id="compare-direct-judge-btn"' in template
    assert 'id="judge-comments"' in template
    assert 'id="judge-session-cost"' in template
    assert 'fetch("/compare/judge"' in script
    assert 'classList.toggle("selected", data.winner === "a")' in script
    assert 'classList.toggle("selected", data.winner === "b")' in script
    assert 'compareAiJudgeBtn.addEventListener("click", copyComparisonPrompt)' in script
