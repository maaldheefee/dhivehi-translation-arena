---
id: TASK-1
title: Return AI analysis ratings in original translation order
status: Done
assignee:
  - '@codex'
created_date: '2026-08-14 04:28'
updated_date: '2026-08-14 04:32'
labels: []
dependencies: []
modified_files:
  - static/js/main.js
  - static/js/compare.js
  - tests/test_analysis_prompts.py
type: enhancement
ordinal: 1000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Improve the copyable translation-analysis prompts so AI judges assign rubric ratings to every translation while preserving the translations' original input/display order. Keep comparative ranking or verdict output separate from the ordered ratings.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The multi-translation analysis prompt requests one rubric rating per option in the exact order supplied
- [x] #2 The pairwise comparison prompt requests ratings for Translation A followed by Translation B
- [x] #3 Prompts clearly separate ordered ratings from best-to-worst rankings or verdicts
- [x] #4 Automated checks cover the ordering instructions
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Extract or expose prompt construction in testable helpers where appropriate. 2. Update multi-translation and pairwise response formats with explicit rubric-aligned ordered ratings. 3. Add regression tests for exact ordering language and run relevant checks.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Updated the multi-translation response format to require rubric ratings in Option 1..N order before a separate best-to-worst ranking. Added the same rubric and an A-then-B ordered ratings section to the pairwise prompt. Validation: node --check passed for both JavaScript files; uv run pytest passed all 78 tests; Ruff passed for the regression test.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
AI analysis prompts now request explicit rubric ratings in original translation order while keeping rankings/verdicts separate. Added ordering regression coverage and verified JavaScript syntax plus the full 78-test suite.
<!-- SECTION:FINAL_SUMMARY:END -->
