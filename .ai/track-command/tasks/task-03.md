# Task 03: Deprecate `gs create` with Warning

## Summary
Keep `gs create` functional but add a deprecation warning suggesting the new workflow. Users should use `git checkout -b <name>` followed by `gs track`.

## Files to Modify
- `gitstacker/commands/create.py`

## Implementation

Add a deprecation warning at the top of `cmd_create()` before any other logic:

```python
from ..output import success, error, info, warning

def cmd_create(args: list[str]) -> None:
    warning("gs create is deprecated. Use: git checkout -b <name> && gs track")
    info("  gs create will be removed in a future version.")
    print()
    
    # ... rest of existing logic unchanged ...
```

If there's no `warning` function in `output.py`, add one (yellow text with ⚠ prefix).

## Acceptance Criteria
- [ ] `gs create` still works exactly as before
- [ ] A visible deprecation warning is printed before execution
- [ ] The warning suggests the new workflow
- [ ] No existing test assertions break (tests that check output may need updating)
