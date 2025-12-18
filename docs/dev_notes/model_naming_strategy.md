# Model Naming & Configuration

## Summary

After discussion, we've settled on the following strategy for model naming and configuration:

### Key Decisions

1. **Database keys always include temperature** - e.g., `gemini-2.0-flash-t0.1`, `claude-opus-4.5-t0.85`
2. **UI visibility controlled by flags** - `is_active` and `is_hidden` (new)
3. **Display names adapt** - Show details when multiple presets, simplify when only one
4. **One preset per model eventually** - After evaluation, deprecate/hide all but the best variant

### Configuration Flags

```python
"is_active": bool    # Can be selected for new translations
"is_hidden": bool    # Hidden from UI selectors (but data still accessible in stats)
```

**Flag combinations:**
- `is_active=True, is_hidden=False` → Available and visible (normal state)
- `is_active=False, is_hidden=False` → Deprecated but visible in stats
- `is_active=False, is_hidden=True` → Fully hidden from UI

### Naming Convention

**Database keys (model IDs):**
```
{base-model}[-{reasoning}]-t{temp}

Examples:
- gemini-2.0-flash-t0.1
- gemini-3-flash-low-t1.0
- claude-opus-4.5-t0.85
```

**Display names:**
- Multiple visible presets: `Gemini 2.0 Flash (T0.1)`, `Gemini 2.0 Flash (T0.85)`
- Single visible preset: `Gemini 2.0 Flash`

### Migration Plan

For model renaming procedures, see [model_renaming.md](model_renaming.md) which documents:
- Step-by-step migration commands
- Rollback procedures
- Common scenarios

### Implementation Tasks

1. **Add `is_hidden` field to ModelConfig TypedDict** in `app/config.py`
2. **Run database migrations** using `scripts/rename_model.py`
3. **Update all model configs** with new keys and `is_hidden` flag
4. **Update UI logic** to respect `is_hidden` flag
5. **Update display name logic** to adapt based on visible preset count
6. **Test thoroughly** before deploying

### Benefits

✅ **Future-proof** - Can change defaults without DB migration  
✅ **Self-documenting** - Temperature always explicit in DB  
✅ **Flexible** - Can show/hide presets without losing data  
✅ **Clean UI** - Simple names when only one preset active  
✅ **Stable** - Model keys never change once set  

### Next Steps

1. Use `scripts/rename_model.py --dry-run` to preview changes
2. Execute migration when ready
3. Update config.py with new model keys
4. Restart application and verify

