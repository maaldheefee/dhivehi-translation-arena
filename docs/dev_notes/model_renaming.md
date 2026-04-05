# Model Renaming Guide

How to safely rename a model identifier across the database and configuration.

## Overview

Model keys are stored as strings in these database tables:

- `translations.model` — Which model generated each translation
- `pairwise_comparisons.winner_model` / `loser_model` — ELO comparison results
- `model_elo.model` — ELO ratings and statistics

Renaming requires updating all references to maintain data integrity.

## When to Rename vs. Deprecate

### Use `is_active: false` (Recommended)

- You want to stop using a model but keep historical data visible
- The model key is acceptable but you want to exclude it from new translations
- You might re-enable it later

### Use Renaming (Advanced)

- The model key has a typo or inconsistent naming
- You are consolidating duplicate model entries
- You need to reorganize naming conventions

## Step-by-Step Process

### Step 1: Backup

```bash
cp data/dhivehi_translation_arena.db data/dhivehi_translation_arena.db.backup
```

### Step 2: Stop the Application

Prevent concurrent writes during migration:

```bash
docker stop dhivehi-translation-arena
```

### Step 3: Dry Run

Preview what would change without committing:

```bash
uv run python scripts/rename_model.py "old-model-key" "new-model-key" --dry-run
```

Review the output — it shows reference counts, conflict checks, and planned changes.

### Step 4: Run the Migration

```bash
uv run python scripts/rename_model.py "old-model-key" "new-model-key"
```

The script prompts for confirmation before making changes and rolls back automatically on errors.

### Step 5: Update `models.yaml`

Rename the key in `models.yaml`, keeping all other fields identical:

```yaml
# Before
old-model-key:
  name: "provider/model-id"
  display_name: "Model Display"
  # ...

# After
new-model-key:
  name: "provider/model-id"
  display_name: "Model Display"
  # ...
```

### Step 6: Restart and Verify

```bash
docker start dhivehi-translation-arena
```

Check:
- Stats page — old translations show under the new name
- ELO rankings — ratings preserved
- Model selector — new name appears
- Create a test translation with the renamed model

## Handling Conflicts (Merging)

If the new key already exists in the database, the script offers to merge:

- Translations keep their data, only the model name changes
- ELO records are combined (counts summed, rating weighted by match count)
- Pairwise comparisons are updated to reference the new name

Do **not** merge when the models are actually different configurations with separate statistics.

## Rollback

1. Stop the application
2. Restore the backup: `cp data/dhivehi_translation_arena.db.backup data/dhivehi_translation_arena.db`
3. Revert `models.yaml`: `git checkout models.yaml`
4. Restart

## Script Safety Features

- **Dry-run mode** — Preview without committing
- **Confirmation prompts** — Requires explicit "yes"
- **Conflict detection** — Warns if new name already exists
- **Transaction rollback** — Automatically rolls back on errors
- **Reference counting** — Shows exactly what will change
- **No data loss** — Only updates model names, never deletes

## Direct SQL Approach

For advanced users:

```sql
BEGIN TRANSACTION;
UPDATE translations SET model = 'new-name' WHERE model = 'old-name';
UPDATE pairwise_comparisons SET winner_model = 'new-name' WHERE winner_model = 'old-name';
UPDATE pairwise_comparisons SET loser_model = 'new-name' WHERE loser_model = 'old-name';
UPDATE model_elo SET model = 'new-name' WHERE model = 'old-name';
COMMIT;
```

This bypasses the script's safety checks — use with caution.
