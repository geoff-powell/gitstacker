# Task 07: Fix Fish Abbreviation Comment Syntax

## Summary
In fish shell, trailing comments on `abbr` lines can be interpreted as part of the abbreviation text. Move comments to separate lines above each abbreviation.

## Files to Modify
- `gitstacker/commands/aliases.py`

## Implementation Details

Change `_fish_aliases()` from:
```python
for alias, command, desc in ALIASES:
    lines.append(f"abbr -a {alias} {command}  # {desc}")
```

To:
```python
for alias, command, desc in ALIASES:
    lines.append(f"# {desc}")
    lines.append(f"abbr -a {alias} {command}")
```

## Acceptance Criteria
- [ ] Fish abbreviations don't include comment text
- [ ] Each abbreviation has a descriptive comment on the line above
- [ ] `gs aliases fish` output is valid fish syntax
