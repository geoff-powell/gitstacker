# Task 04: Add Auto-Track Guards to Stack Commands

## Summary
When a user runs a stack manipulation command while on an untracked branch, offer to track the branch instead of just printing an error.

## Files to Modify
- `gitstacker/store.py` — add `offer_track_current_branch()` utility
- `gitstacker/commands/navigate.py` — add guard
- `gitstacker/commands/modify.py` — add guard
- `gitstacker/commands/restack.py` — add guard  
- `gitstacker/commands/submit.py` — add guard
- `gitstacker/commands/diff.py` — add guard

## Implementation

### Utility Function (in `store.py` or new `gitstacker/prompts.py`)

```python
def offer_track_current_branch(state: dict, branch: str) -> Optional[dict]:
    """If branch is not tracked, offer to track it.
    
    Returns the stack if tracking succeeded, None if user declined.
    Raises SystemExit if user declines.
    """
    from .commands.track import track_branch
    
    stack = get_current_stack(state, branch)
    if stack:
        return stack
    
    # Branch is not tracked
    print(f'Branch "{branch}" is not tracked in any stack.')
    response = input("Track it now? [Y/n]: ").strip().lower()
    
    if response in ("", "y", "yes"):
        track_branch(branch, state)
        return get_current_stack(state, branch)
    else:
        raise SystemExit(1)
```

### Guard Pattern in Commands
Replace patterns like:
```python
stack = get_current_stack(state, current_branch)
if not stack:
    error("Not on a stacked branch...")
    raise SystemExit(1)
```

With:
```python
stack = get_current_stack(state, current_branch)
if not stack:
    stack = offer_track_current_branch(state, current_branch)
```

### Which Commands Get the Guard
- `gs up` / `gs down` / `gs top` / `gs bottom` — navigation
- `gs modify` — modification
- `gs restack` — rebasing
- `gs submit` — PR submission
- `gs diff` — diff viewing

Commands that should NOT get the guard (they have different error paths):
- `gs log` — can show "no stack" info without prompting
- `gs status` — informational, shouldn't prompt
- `gs delete` — explicit removal, shouldn't auto-track

## Acceptance Criteria
- [ ] Running `gs up` on an untracked branch prompts to track
- [ ] User can accept (Y) and command continues after tracking
- [ ] User can decline (n) and command exits
- [ ] If no stack exists, gives appropriate error (can't track without a stack)
- [ ] Non-interactive environments (piped stdin) don't hang
