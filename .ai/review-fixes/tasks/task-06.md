# Task 06: Rename gst Alias to gstop

## Summary
Rename the `gst` alias (for `gs top`) to `gstop` to avoid conflicts with common `git stash` aliases and the GNU Smalltalk binary.

## Files to Modify
- `gitstacker/commands/aliases.py`

## Implementation Details

In the `ALIASES` list, change:
```python
("gst", "gs top", "Jump to top of stack"),
```

To:
```python
("gstop", "gs top", "Jump to top of stack"),
```

## Acceptance Criteria
- [ ] `gst` is no longer defined as an alias
- [ ] `gstop` maps to `gs top`
- [ ] No other aliases are changed
