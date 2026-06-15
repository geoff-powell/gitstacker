# Task 02: Retry-Create on Update Failure (TOCTOU Fix)

## Summary
In `upsert_stack_comment()`, if `_update_comment()` returns False (e.g., comment was deleted between find and update — a TOCTOU race), fall through to `_create_comment()` instead of silently returning False.

## Files to Modify
- `gitstacker/github.py`

## Implementation Details

Change `upsert_stack_comment()` from:

```python
if existing_id:
    return _update_comment(existing_id, body)
else:
    return _create_comment(pr_number, body)
```

To:

```python
if existing_id:
    if _update_comment(existing_id, body):
        return True
    # Comment was deleted between find and update — fall through to create

return _create_comment(pr_number, body)
```

## Acceptance Criteria
- [ ] If `_update_comment` succeeds, returns True
- [ ] If `_update_comment` fails (comment deleted), falls through to `_create_comment`
- [ ] If no existing comment found, creates a new one (unchanged behavior)
