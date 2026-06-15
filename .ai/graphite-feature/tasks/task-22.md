# Task 22: Implement `gs freeze` and `gs unfreeze` Commands

## Description
Add `gs freeze [branch]` and `gs unfreeze [branch]` commands that mark branches as frozen/unfrozen. Frozen branches are skipped during restack and cannot be modified or have new branches created on top of them.

## Dependencies
- Task 21 (restack_from already has skip_frozen parameter)

## Affected Files
- `gitstacker/commands/freeze.py` — **new** (freeze and unfreeze commands)
- `gitstacker/store.py` — add `frozen` field default in `_validate_state()`
- `gitstacker/commands/create.py` — add frozen parent check
- `gitstacker/commands/log.py` — display frozen indicator
- `gitstacker/output.py` — add frozen symbol constant

## Implementation Details

### New file: `gitstacker/commands/freeze.py`

```python
"""gs freeze / gs unfreeze - Mark branches as frozen to prevent modifications."""

from ..store import load_state, save_state, get_current_stack
from ..git_ops import get_current_branch
from ..output import success, error, info, bold


def cmd_freeze(args: list[str]) -> None:
    """Freeze a branch to prevent modifications and skip during restack."""
    state = load_state()
    
    # Determine target branch
    branch = args[0] if args else get_current_branch()
    
    # Validate branch is tracked
    if branch not in state["branches"]:
        error(f'"{branch}" is not a stacked branch.')
        info("Only branches managed by GitStacker can be frozen.")
        raise SystemExit(1)
    
    # Check if already frozen
    if state["branches"][branch].get("frozen", False):
        info(f'"{bold(branch)}" is already frozen.')
        return
    
    # Freeze it
    state["branches"][branch]["frozen"] = True
    save_state(state)
    success(f'Froze "{bold(branch)}" — it will be skipped during restack and cannot be modified.')


def cmd_unfreeze(args: list[str]) -> None:
    """Unfreeze a branch to allow modifications and restacking."""
    state = load_state()
    
    # Determine target branch
    branch = args[0] if args else get_current_branch()
    
    # Validate branch is tracked
    if branch not in state["branches"]:
        error(f'"{branch}" is not a stacked branch.')
        info("Only branches managed by GitStacker can be unfrozen.")
        raise SystemExit(1)
    
    # Check if not frozen
    if not state["branches"][branch].get("frozen", False):
        info(f'"{bold(branch)}" is not frozen.')
        return
    
    # Unfreeze it
    state["branches"][branch]["frozen"] = False
    save_state(state)
    success(f'Unfroze "{bold(branch)}" — it will now be included in restack and can be modified.')
```

### Modify `gitstacker/store.py` — `_validate_state()`

In the branch validation loop (around line 68-78), add `frozen` default:

```python
    # Validate each branch entry
    for name, meta in list(state["branches"].items()):
        if not isinstance(meta, dict):
            del state["branches"][name]
            continue
        if "name" not in meta:
            meta["name"] = name
        if "parent" not in meta or not isinstance(meta["parent"], str):
            meta["parent"] = state["trunk"]
        meta.setdefault("pr_number", None)
        meta.setdefault("pr_url", None)
        meta.setdefault("commit_base", None)
        meta.setdefault("frozen", False)  # <-- ADD THIS LINE
```

### Modify `gitstacker/commands/create.py` — frozen parent check

After finding the current stack and before creating the branch, add:

```python
    # Check if current branch (the parent) is frozen
    current_branch = get_current_branch()
    if current_branch in state["branches"] and state["branches"][current_branch].get("frozen", False):
        error(f'Cannot create on top of frozen branch "{current_branch}".')
        info(f'Unfreeze it first: gs unfreeze {current_branch}')
        raise SystemExit(1)
```

### Modify `gitstacker/output.py` — add frozen symbol

Add a constant for the frozen indicator:

```python
FROZEN_SYMBOL = "\u2744"  # snowflake: ❄
# Or for ASCII fallback:
# FROZEN_SYMBOL = "[frozen]"
```

### Modify `gitstacker/commands/log.py` — show frozen indicator

In the branch display loop, after the branch name, append the frozen indicator:

```python
    frozen_mark = f" {FROZEN_SYMBOL}" if meta.get("frozen", False) else ""
    # Include frozen_mark in the branch line output
```

## Acceptance Criteria
- [ ] `gs freeze` marks the current branch as frozen in state.json
- [ ] `gs freeze <name>` marks a specific branch as frozen
- [ ] `gs unfreeze` removes frozen status from current branch
- [ ] `gs unfreeze <name>` removes frozen status from a specific branch
- [ ] Freezing an already-frozen branch shows info message (not error)
- [ ] Unfreezing a non-frozen branch shows info message (not error)
- [ ] Freezing a non-stacked branch errors with clear message
- [ ] `_validate_state()` defaults `frozen` to `False` for backward compatibility
- [ ] `gs create` on top of a frozen branch is blocked with clear error
- [ ] `gs log` shows frozen indicator (snowflake) next to frozen branches
- [ ] Existing state files without `frozen` field load without errors
