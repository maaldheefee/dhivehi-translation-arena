---
trigger: always_on
---

When running dev scripts, use uv with DATA_DIR.

`export DATA_DIR='/DATA/AppData/dhivehi-translation-arena/' && uv run` ...

The db file name is `/DATA/AppData/dhivehi-translation-arena/dhivehi_translation_arena.db`

Keep in mind that the prod container will be connected to the DB in the background