# Domain Docs

This is a single-context repository.

## Before exploring, read these

- `CONTEXT.md` at the repository root.
- Relevant architectural decisions under `docs/adr/`.

If either location does not exist, proceed silently. The producer skill creates
domain documentation lazily when terms or decisions are resolved.

## Use the glossary's vocabulary

When output names a domain concept, use the term defined in `CONTEXT.md`. Do not
drift to synonyms the glossary explicitly avoids.

If a needed concept is absent from the glossary, reconsider the terminology or
note the gap for a domain-documentation session.

## Flag ADR conflicts

Explicitly identify any proposal that contradicts an accepted architectural
decision rather than silently overriding it.
