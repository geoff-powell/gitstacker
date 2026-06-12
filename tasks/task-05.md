# Task 05: Fix Navigation Bugs

## Description
Fix three bugs in the navigation system: (1) `up` from trunk incorrectly goes to top instead of bottom, (2) `gs up abc` crashes with ValueError instead of showing a helpful error, (3) no dirty working tree check before navigate. Also fix the `trunk.py` bug where setting trunk doesn't offer to update existing stacks.

## Files to Create/Modify
- `gitstacker/commands/navigate.py` — Fix trunk navigation direction, validate numeric args, add dirty tree check
- `gitstacker/commands/trunk.py` — Warn about stacks referencing old trunk when trunk is changed

## Implementation Details

### Fix 1: Trunk navigation direction (Bug #4)
In `cmd_navigate()`, when on trunk with `direction == "up"`, it should go to `branches[0]` (bottom of stack), not `branches[-1]` (top). The current code sends `up` to top:

```python
# CURRENT (wrong):
if direction in ("bottom", "down"):
    target = target_stack["branches"][0]
else:
    target = target_stack["branches"][-1]

# FIXED:
if direction in ("up", "bottom"):
    target = target_stack["branches"][0]
elif direction in ("top",):
    target = target_stack["branches"][-1]
elif direction == "down":
    # Can't go down from trunk
    warn("Already at the bottom (trunk).")
    return
```

Logic: From trunk, "up" means "go into the stack" = bottom branch. "top" means "jump to top". "down" from trunk is nonsensical.

### Fix 2: ValueError on non-numeric args (Bug #8)
The line `count = int(args[0]) if args else 1` crashes on non-numeric input:

```python
# FIXED:
if args:
    try:
        count = int(args[0])
    except ValueError:
        error(f'Invalid count: "{args[0]}". Expected a number.')
        raise SystemExit(1)
    if count < 1:
        error("Count must be at least 1.")
        raise SystemExit(1)
else:
    count = 1
```

### Fix 3: Dirty working tree check (Bug #6 - partial)
Add a check at the top of `cmd_navigate()`:

```python
from ..git_ops import is_working_tree_clean

def cmd_navigate(direction: str, args: list[str]) -> None:
    if not is_working_tree_clean():
        error("Working tree has uncommitted changes.")
        info("Commit or stash your changes before navigating.")
        raise SystemExit(1)
    # ... rest of function
```

### Fix 4: Trunk set warns about stacks (Bug #11)
In `trunk.py`, after changing trunk, check if any stacks reference the old trunk:

```python
def cmd_trunk(args: list[str]) -> None:
    state = load_state()

    if not args:
        info(f"Trunk branch: {state['trunk']}")
        return

    new_trunk = args[0]
    if not branch_exists(new_trunk):
        error(f'Branch "{new_trunk}" does not exist.')
        raise SystemExit(1)

    old_trunk = state["trunk"]
    state["trunk"] = new_trunk

    # Warn about stacks referencing old trunk
    affected = [s["name"] for s in state["stacks"].values() if s["trunk"] == old_trunk]
    if affected:
        for name in affected:
            state["stacks"][name]["trunk"] = new_trunk
        warn(f"Updated {len(affected)} stack(s) to use new trunk: {', '.join(affected)}")

    save_state(state)
    success(f"Trunk branch set to: {new_trunk}")
```

## Dependencies
- Depends on: task-01 (state validation)

## Acceptance Criteria
- [ ] `gs up` from trunk goes to `branches[0]` (bottom of stack), not top
- [ ] `gs top` from trunk goes to `branches[-1]` (top of stack)
- [ ] `gs down` from trunk shows "already at bottom" warning
- [ ] `gs up abc` shows "Invalid count" error message, exits 1
- [ ] `gs up -1` shows "Count must be at least 1" error, exits 1
- [ ] `gs up` with dirty working tree shows error about uncommitted changes
- [ ] `gs trunk new-branch` updates all stacks that referenced the old trunk
- [ ] All changes are backward-compatible with existing behavior for valid inputs

## Notes
- The dirty tree check may need a `--force` flag bypass for power users — skip that for now, add in task-17.
- The trunk update behavior is auto-applied (not interactive) since we can't prompt in a CLI tool easily.
- `bottom` direction from trunk should still go to `branches[0]` (which it already does correctly).
