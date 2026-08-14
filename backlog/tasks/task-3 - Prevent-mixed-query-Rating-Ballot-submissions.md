---
id: TASK-3
title: Prevent mixed-query Rating Ballot submissions
status: Done
assignee:
  - '@codex'
created_date: '2026-08-14 06:05'
updated_date: '2026-08-14 06:10'
labels: []
dependencies: []
modified_files:
  - app/blueprints/main.py
  - app/services/vote_service.py
  - static/js/main.js
  - tests/test_main_routes.py
  - tests/test_ui_contract.py
priority: high
type: bug
ordinal: 3000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Voting can fail with 'Every rated translation must belong to the ballot query' when a retry or stale stream result inserts a Translation from a different Query into the active result set. Keep the browser result set bound to one immutable Query and return an appropriate client error for invalid ballot payloads.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Retrying a failed translation cannot attach a Translation from a different Query to the active result set
- [x] #2 Stale or mismatched streamed Translation results are not included in a Rating Ballot
- [x] #3 A mixed-query ballot receives a non-500 client error response and records no votes
- [x] #4 Regression tests cover the mixed-query request and frontend query-binding behavior
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Add failing regression tests for mixed-query route status and immutable retry/query binding. 2. Bind each translation run to its original source text and query ID; ignore mismatched or stale stream callbacks. 3. Map ballot validation failures to a 400 response while preserving server-error handling. 4. Run focused and full test suites, then finalize the task.

5. Normalize browser string query IDs at the route boundary after the exact production request shape revealed the primary type mismatch.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Root cause confirmed: the browser serialized the hidden query ID as a string, while strict Translation query validation compared it with integer database IDs. Added route normalization, immutable frontend run/query binding, stale stream guards, retry binding to the original source text, and client-error status mapping. Verification: 95 pytest tests pass; changed-file Ruff checks pass; node --check passes; git diff --check passes. Repository-wide Ruff still has six unrelated pre-existing violations in app/__init__.py, app/cli.py, and app/services/user_service.py.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Fixed vote submission by normalizing browser query IDs before Translation ownership validation and binding each frontend evaluation run, retry, stream callback, and rated card to one Query. Verified with exact string-ID and mixed-query route regressions, frontend contract coverage, 95 passing pytest tests, changed-file Ruff, JavaScript syntax validation, and whitespace checks.
<!-- SECTION:FINAL_SUMMARY:END -->
