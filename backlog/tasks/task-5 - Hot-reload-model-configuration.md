---
id: TASK-5
title: Hot-reload model configuration
status: Done
assignee:
  - '@codex'
created_date: '2026-08-14 09:35'
updated_date: '2026-08-14 09:39'
labels: []
dependencies: []
modified_files:
  - app/config.py
  - tests/test_config.py
type: enhancement
ordinal: 5000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Allow operators to edit models.yaml and have valid model changes take effect in a running application without restarting it. Preserve the last known-good configuration when a save is malformed or incomplete.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A valid models.yaml change becomes visible to subsequent requests without restarting the application
- [x] #2 An invalid or partially written models.yaml does not replace the last known-good model configuration
- [x] #3 Reload behavior is safe under concurrent request access
- [x] #4 Automated tests cover unchanged, valid-change, and invalid-change behavior
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Add a thread-safe model configuration reloader that detects file-version changes and retains the last valid snapshot. 2. Refresh the cached Config instance whenever get_config() is called, keeping existing call sites unchanged. 3. Add focused tests for unchanged files, valid changes, invalid changes, and recovery. 4. Run configuration and broader tests.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Implemented a thread-safe last-known-good models.yaml reloader and wired it into get_config(). Added tests for unchanged snapshots, valid reloads through get_config(), malformed-save recovery, and concurrent readers. Verification: 106 tests passed; Ruff and ty passed for changed files.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added dependency-free hot loading for models.yaml at the existing get_config() access boundary. Valid edits are atomically exposed to subsequent calls; malformed or missing saves log an error and retain the last valid snapshot; a lock prevents duplicate concurrent reloads. Verified by 21 focused configuration tests, the full 106-test suite, Ruff, ty, and git diff checks.
<!-- SECTION:FINAL_SUMMARY:END -->
