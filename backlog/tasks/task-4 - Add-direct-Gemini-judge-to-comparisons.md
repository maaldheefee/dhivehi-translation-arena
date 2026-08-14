---
id: TASK-4
title: Add direct Gemini judge to comparisons
status: Done
assignee:
  - '@codex'
created_date: '2026-08-14 07:34'
updated_date: '2026-08-14 07:36'
labels: []
dependencies: []
type: feature
ordinal: 4000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Allow users to have Google Gemini 3.7 Flash judge a comparison directly through the API while retaining the existing copy-prompt manual AI workflow. Record judge cost in the browser session, highlight the preferred item, and display optional judge comments.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The existing manual copy-prompt AI judging workflow remains available
- [x] #2 A comparison offers a button that calls google/gemini-3.7-flash as judge
- [x] #3 A successful judge response highlights the preferred item and displays comments when supplied
- [x] #4 Judge API cost is recorded and included in the session total cost
- [x] #5 Automated tests cover direct judging, result handling, and cost accounting
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Add a structured OpenRouter judge service. 2. Add an authenticated comparison judge endpoint with validation and session cost accounting. 3. Add direct-judge UI while preserving prompt copy. 4. Add focused tests and run quality checks.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Implemented structured OpenRouter judging with the exact requested model ID. Cost uses OpenRouter's billed usage.cost rather than hard-coded pricing. Session cost persists in Flask session and is returned with comparisons. Validation: 99 pytest tests passed; focused Ruff and git diff checks passed. Whole-repository Ruff still reports six unrelated pre-existing violations in app/__init__.py, app/cli.py, and app/services/user_service.py.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added direct Gemini judging alongside the retained prompt-copy workflow. The API validates the pair, returns a structured winner and optional comments, tracks OpenRouter-billed cost in the comparison session, and the UI highlights the result and continuously shows session judge cost. Verified by 99 passing tests plus focused Ruff and diff checks.
<!-- SECTION:FINAL_SUMMARY:END -->
