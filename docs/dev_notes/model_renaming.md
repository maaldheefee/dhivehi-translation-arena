# Model Renaming Guide

This guide explains how to safely rename a model identifier in the Dhivehi Translation Arena application.

## Overview

Model identifiers (keys in `config.py`) are stored as strings throughout the database in multiple tables:
- `translations.model` - Which model generated each translation
- `pairwise_comparisons.winner_model` / `loser_model` - ELO comparison results
- `model_elo.model` - ELO ratings and statistics

Renaming a model requires updating all these references to maintain data integrity.

## When to Rename vs. Deprecate

### Use `is_active: False` (Recommended)
- You want to stop using a model but keep historical data visible
- The model name is acceptable but you want to exclude it from new translations
- You might re-enable it later

### Use Renaming (Advanced)
- The model key has a typo or inconsistent naming
- You're consolidating duplicate model entries
- You need to reorganize model naming conventions

## Prerequisites

1. **Backup your database** before any migration:
   ```bash
   cp /DATA/AppData/dhivehi-translation-arena/dhivehi_translation_arena.db \
      /DATA/AppData/dhivehi-translation-arena/dhivehi_translation_arena.db.backup
   ```

2. **Stop the application** to prevent concurrent writes:
   ```bash
   # Stop the production container
   docker stop dhivehi-translation-arena
   
   # Or stop the dev server
   # Press Ctrl+C in the terminal running `just dev`
   ```

## Step-by-Step Renaming Process

### Step 1: Dry Run (Safe Preview)

First, run the migration script in dry-run mode to see what would change:

```bash
cd /DATA/Repos/dhivehi-translation-arena-1

# Set the data directory
export DATA_DIR='/DATA/AppData/dhivehi-translation-arena/'

# Run dry-run
uv run python scripts/rename_model.py "old-model-name" "new-model-name" --dry-run
```

**Example:**
```bash
uv run python scripts/rename_model.py "gemini-3-flash-t1.0" "gemini-3-flash-default" --dry-run
```

The script will show:
- How many records reference the old name
- Whether the new name already exists (conflict check)
- What changes would be made

### Step 2: Review the Output

The dry run will display something like:

```
============================================================
Model Rename Migration: 'gemini-3-flash-t1.0' → 'gemini-3-flash-default'
Mode: DRY RUN (no changes will be made)
============================================================

Step 1: Counting existing references...
Found 42 total references:
  - translations: 35
  - comparisons_winner: 4
  - comparisons_loser: 2
  - elo_records: 1

Step 2: Checking for conflicts...
✓ No conflicts found - 'gemini-3-flash-default' is available

Step 3: Updating database records...
  Updating 35 translation records...
  Updating 4 comparison records (winner)...
  Updating 2 comparison records (loser)...
  Updating 1 ELO record(s)...

✓ Dry run completed - no changes were made
```

### Step 3: Perform the Actual Migration

If the dry run looks good, run the actual migration:

```bash
uv run python scripts/rename_model.py "old-model-name" "new-model-name"
```

**You will be prompted twice for confirmation:**
1. Before starting the migration
2. If there are conflicts with the new name

### Step 4: Update config.py

After the database migration succeeds, update `app/config.py`:

```python
# Before:
MODELS = {
    "old-model-name": {
        "name": "google/gemini-3-flash-preview",
        "display_name": "Gemini 3 Flash",
        # ... rest of config
    },
}

# After:
MODELS = {
    "new-model-name": {  # ← Changed key
        "name": "google/gemini-3-flash-preview",
        "display_name": "Gemini 3 Flash",
        # ... rest of config (unchanged)
    },
}
```

**Important:** Only change the dictionary key. Keep all other configuration identical.

### Step 5: Restart and Verify

1. **Restart the application:**
   ```bash
   # Production
   docker start dhivehi-translation-arena
   
   # Or development
   just dev
   ```

2. **Verify in the UI:**
   - Check the stats page - old translations should show under the new name
   - Check ELO rankings - ratings should be preserved
   - Check model selector - new name should appear
   - Try creating a new translation with the renamed model

## Handling Conflicts (Merging Models)

If the new name already exists in the database, the script will offer to merge them:

```
⚠️  WARNING: New name 'new-model-name' already exists in:
  - translations
  - elo_records

This will merge data from both models. Continue? (yes/no):
```

**What happens during a merge:**
- All translations keep their original data (just model name changes)
- ELO records are combined:
  - Win/loss/tie counts are summed
  - ELO rating is weighted average based on match counts
- Pairwise comparisons are updated to reference the new name

**When to merge:**
- You accidentally created duplicate model entries
- You want to consolidate variants into a single model

**When NOT to merge:**
- The models are actually different (different configurations)
- You want to keep separate statistics

## Rollback Procedure

If something goes wrong:

1. **Stop the application immediately**

2. **Restore from backup:**
   ```bash
   cp /DATA/AppData/dhivehi-translation-arena/dhivehi_translation_arena.db.backup \
      /DATA/AppData/dhivehi-translation-arena/dhivehi_translation_arena.db
   ```

3. **Revert config.py changes:**
   ```bash
   git checkout app/config.py
   ```

4. **Restart the application**

## Script Safety Features

The migration script includes several safety mechanisms:

1. **Dry-run mode** - Preview changes without committing
2. **Confirmation prompts** - Requires explicit "yes" to proceed
3. **Conflict detection** - Warns if new name already exists
4. **Transaction rollback** - Automatically rolls back on errors
5. **Reference counting** - Shows exactly what will change
6. **No data loss** - Only updates model names, never deletes data

## Common Scenarios

### Scenario 1: Fix a Typo

```bash
# Dry run first
uv run python scripts/rename_model.py "gemini-3-flash-t1.0" "gemini-3-flash-temp-1.0" --dry-run

# If looks good, run it
uv run python scripts/rename_model.py "gemini-3-flash-t1.0" "gemini-3-flash-temp-1.0"

# Update config.py
# Restart app
```

### Scenario 2: Consolidate Duplicates

If you accidentally created two entries for the same model:

```bash
# This will merge their statistics
uv run python scripts/rename_model.py "duplicate-model-1" "canonical-model-name"
```

### Scenario 3: Reorganize Naming Convention

To rename multiple models to a new convention:

```bash
# Rename each one individually
uv run python scripts/rename_model.py "gemini-3-flash-t1.0" "gemini-3-flash-default"
uv run python scripts/rename_model.py "gemini-3-flash-low-t1.0" "gemini-3-flash-low-reasoning"
# ... etc

# Update all keys in config.py at once
# Restart app
```

## Troubleshooting

### "No references found for model"
- The old model name doesn't exist in the database
- Check for typos in the old name
- Query the database to see what models exist:
  ```bash
  sqlite3 /DATA/AppData/dhivehi-translation-arena/dhivehi_translation_arena.db \
    "SELECT DISTINCT model FROM translations;"
  ```

### "Error during migration"
- The script automatically rolls back changes
- Check the error message for details
- Ensure the database file is writable
- Make sure no other process is accessing the database

### Changes not appearing in UI
- Did you update `config.py`?
- Did you restart the application?
- Check browser cache (hard refresh with Ctrl+Shift+R)

## Alternative: SQL Direct Approach

For advanced users, you can also rename models directly with SQL:

```bash
sqlite3 /DATA/AppData/dhivehi-translation-arena/dhivehi_translation_arena.db
```

```sql
BEGIN TRANSACTION;

-- Update all references
UPDATE translations SET model = 'new-name' WHERE model = 'old-name';
UPDATE pairwise_comparisons SET winner_model = 'new-name' WHERE winner_model = 'old-name';
UPDATE pairwise_comparisons SET loser_model = 'new-name' WHERE loser_model = 'old-name';
UPDATE model_elo SET model = 'new-name' WHERE model = 'old-name';

-- Verify changes
SELECT COUNT(*) FROM translations WHERE model = 'new-name';
SELECT COUNT(*) FROM pairwise_comparisons WHERE winner_model = 'new-name' OR loser_model = 'new-name';
SELECT * FROM model_elo WHERE model = 'new-name';

-- If everything looks good:
COMMIT;

-- If something is wrong:
-- ROLLBACK;
```

**Warning:** This approach requires manual verification and doesn't include the safety checks of the Python script.

## Summary

**Recommended workflow:**
1. ✅ Backup database
2. ✅ Stop application
3. ✅ Run dry-run migration
4. ✅ Review output carefully
5. ✅ Run actual migration
6. ✅ Update config.py
7. ✅ Restart application
8. ✅ Verify in UI

**Remember:** For most cases, using `is_active: False` is simpler and safer than renaming!
