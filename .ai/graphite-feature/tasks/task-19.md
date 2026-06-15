# Task 19: Implement `gs undo` Command

## Description
Create the `gs undo` command that reverts the last mutating GitStacker operation by restoring both `state.json` and git branch positions from the journal snapshot.

## Dependencies
- Task 18 (journal.py must exist)

## Affected Files
- `gitstacker/commands/undo.py` — **new** (command implementation)

## Implementation Details

### New file: `gitstacker/commands/undo.py`

```python
"""gs undo - Revert the last mutating GitStacker operation."""

import sys
from ..journal import get_last_entry, remove_last_entry, snapshot_before, load_journal, save_journal
from ..store import save_state, load_state
from ..git_ops import (
    get_current_branch, checkout, is_working_tree_clean,
    reset_branch_to_sha, git,
)
from ..output import success, error, info, warn, bold, dim


def cmd_undo(args: list[str]) -> None:
    """Undo the last mutating operation."""
    
    # Check for dirty tree
    if not is_working_tree_clean():
        error("Working tree has uncommitted changes.")
        info("Commit or stash your changes before undoing.")
        raise SystemExit(1)
    
    # Get last journal entry
    entry = get_last_entry()
    if not entry:
        error("Nothing to undo.")
        info("The undo journal is empty — no mutating operations have been recorded.")
        raise SystemExit(1)
    
    operation = entry.get("operation", "unknown")
    timestamp = entry.get("timestamp", "unknown")
    
    # Show what will be undone
    print()
    info(f"Undoing {bold(operation)} from {dim(timestamp)}...")
    print()
    
    # Before undoing, snapshot current state (so undo-of-undo works)
    try:
        current_state = load_state()
        snapshot_before("undo", current_state)
    except RuntimeError:
        pass  # State might be in a bad place; proceed anyway
    
    # Restore state.json
    pre_state = entry.get("pre_state")
    if pre_state:
        save_state(pre_state)
        info("Restored state.json")
    else:
        warn("No state snapshot found in journal entry — state not restored.")
    
    # Restore branch positions
    branch_shas = entry.get("branch_shas", {})
    restored_count = 0
    skipped = []
    
    for branch, sha in branch_shas.items():
        # Verify SHA is reachable
        verify = git("cat-file", "-t", sha)
        if not verify.success:
            skipped.append(branch)
            continue
        
        result = reset_branch_to_sha(branch, sha)
        if result.success:
            restored_count += 1
        else:
            skipped.append(branch)
    
    if restored_count > 0:
        info(f"Reset {restored_count} branch(es) to previous positions")
    
    if skipped:
        warn(f"Could not restore: {', '.join(skipped)} (SHAs unreachable or branch conflicts)")
    
    # Return to the original HEAD position
    head_branch = entry.get("head_branch")
    if head_branch and head_branch != "HEAD":
        try:
            checkout(head_branch)
            info(f"Returned to: {bold(head_branch)}")
        except RuntimeError as e:
            warn(f"Could not checkout {head_branch}: {e}")
    
    # Remove the consumed entry (the one we just undid)
    # Note: snapshot_before("undo") already added a new entry at position 0,
    # so the entry we consumed is now at position 1
    journal = load_journal()
    if len(journal) > 1:
        journal.pop(1)  # Remove the consumed entry (shifted to pos 1 by snapshot_before)
        save_journal(journal)
    
    print()
    success(f"Undid {bold(operation)} successfully!")
```

### Key behaviors:
1. **Dirty tree check** — refuses to undo if uncommitted changes exist (they'd be lost)
2. **Records itself** — before undoing, snapshots current state so `gs undo` again = redo
3. **Restores state.json** — replaces current state with pre-operation snapshot
4. **Resets branch pointers** — uses `git branch -f <name> <sha>` for each tracked branch
5. **Verifies SHAs** — checks `git cat-file -t <sha>` before resetting (handles GC'd commits)
6. **Returns to original branch** — checks out the branch user was on before the undone operation
7. **Removes consumed entry** — so repeated `gs undo` walks back through history

## Acceptance Criteria
- [ ] `gs undo` with empty journal shows "Nothing to undo" error
- [ ] `gs undo` with dirty tree warns and aborts
- [ ] `gs undo` restores state.json to pre-operation snapshot
- [ ] `gs undo` resets all tracked branch pointers via `git branch -f`
- [ ] `gs undo` returns user to their original branch
- [ ] `gs undo` verifies SHAs are reachable before resetting
- [ ] Unreachable SHAs are skipped with a warning (not a crash)
- [ ] `gs undo` records itself in journal (undo-of-undo works)
- [ ] After undo, the consumed journal entry is removed
- [ ] Output clearly shows what was undone (operation name + timestamp)
