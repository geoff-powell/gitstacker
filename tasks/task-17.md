# Task 17: Add Dirty Working Tree Handling to All Commands

## Description
Add consistent dirty working tree detection and handling to all commands that modify the working tree (navigate, switch, sync, delete). Commands should refuse to proceed with uncommitted changes unless the user explicitly stashes or commits first. This prevents accidental data loss from context switches.

## Files to Create/Modify
- `gitstacker/commands/navigate.py` — Already has check from Task 05, verify it's there
- `gitstacker/commands/stack.py` — Add check to `stack_switch()`
- `gitstacker/commands/sync.py` — Add check before sync begins
- `gitstacker/commands/delete.py` — Add check when delete would change branch
- `gitstacker/commands/create.py` — Add check (create switches branches)
- `tests/integration/test_dirty_tree.py` — Tests for dirty tree handling across commands

## Implementation Details

### Extract a shared helper

Create a helper to avoid duplicating the check everywhere. Add to `git_ops.py`:

```python
def require_clean_tree() -> None:
    """Raise SystemExit if working tree is dirty.

    Call this at the top of any command that will change branches.
    """
    if not is_working_tree_clean():
        from .output import error, info
        error("Working tree has uncommitted changes.")
        info("Commit or stash your changes first, then retry.")
        raise SystemExit(1)
```

Or alternatively, keep the check inline in each command for clearer error messages.

### Commands to update:

**navigate.py** (verify already done in Task 05):
```python
def cmd_navigate(direction: str, args: list[str]) -> None:
    if not is_working_tree_clean():
        error("Working tree has uncommitted changes.")
        info("Commit or stash your changes before navigating.")
        raise SystemExit(1)
```

**stack.py** — `stack_switch`:
```python
def stack_switch(args: list[str]) -> None:
    if not args:
        error("Stack name required. Usage: gs stack switch <name>")
        raise SystemExit(1)

    from ..git_ops import is_working_tree_clean
    if not is_working_tree_clean():
        error("Working tree has uncommitted changes.")
        info("Commit or stash your changes before switching stacks.")
        raise SystemExit(1)

    # ... rest unchanged
```

**sync.py** — Before the sync begins:
```python
def cmd_sync(args: list[str]) -> None:
    from ..git_ops import is_working_tree_clean
    if not is_working_tree_clean():
        error("Working tree has uncommitted changes.")
        info("Commit or stash your changes before syncing.")
        raise SystemExit(1)

    # ... rest unchanged (remove the stash logic from restack since we block earlier)
```

**delete.py** — Only if delete will change branches:
```python
def cmd_delete(args: list[str]) -> None:
    state = load_state()
    # ... get branch ...
    current_branch = get_current_branch()

    if current_branch == branch:
        from ..git_ops import is_working_tree_clean
        if not is_working_tree_clean():
            error("Working tree has uncommitted changes.")
            info("Commit or stash your changes before deleting the current branch.")
            raise SystemExit(1)
    # ... rest unchanged
```

**create.py** — Creating switches to new branch:
```python
def cmd_create(args: list[str]) -> None:
    if not args:
        error("Branch name required. Usage: gs create <branch-name>")
        raise SystemExit(1)

    from .git_ops import is_working_tree_clean
    if not is_working_tree_clean():
        error("Working tree has uncommitted changes.")
        info("Commit or stash your changes before creating a new branch.")
        raise SystemExit(1)

    # ... rest unchanged
```

### test_dirty_tree.py

```python
import pytest
from gitstacker.commands.navigate import cmd_navigate
from gitstacker.commands.stack import cmd_stack
from gitstacker.commands.sync import cmd_sync
from gitstacker.commands.delete import cmd_delete
from gitstacker.commands.create import cmd_create
from gitstacker.git_ops import get_current_branch, checkout


class TestDirtyTreeBlocking:
    """All commands refuse to run with dirty working tree."""

    def _make_dirty(self, repo):
        """Create an uncommitted file."""
        (repo / "dirty.txt").write_text("uncommitted changes")

    def test_navigate_blocked(self, stacked_repo):
        checkout("branch-1")
        self._make_dirty(stacked_repo)
        with pytest.raises(SystemExit):
            cmd_navigate("up", [])
        # Verify we didn't move
        assert get_current_branch() == "branch-1"

    def test_stack_switch_blocked(self, stacked_repo):
        checkout("branch-1")
        self._make_dirty(stacked_repo)
        # Create second stack to switch to
        from gitstacker.store import load_state, save_state, create_stack
        state = load_state()
        create_stack(state, "other-stack")
        save_state(state)
        with pytest.raises(SystemExit):
            cmd_stack(["switch", "other-stack"])
        assert get_current_branch() == "branch-1"

    def test_create_blocked(self, stacked_repo):
        checkout("branch-1")
        self._make_dirty(stacked_repo)
        with pytest.raises(SystemExit):
            cmd_create(["new-branch"])
        # Branch should not have been created
        from gitstacker.git_ops import branch_exists
        assert not branch_exists("new-branch")

    def test_sync_blocked(self, stacked_repo):
        checkout("branch-1")
        self._make_dirty(stacked_repo)
        with pytest.raises(SystemExit):
            cmd_sync([])

    def test_delete_current_branch_blocked(self, stacked_repo):
        checkout("branch-3")
        self._make_dirty(stacked_repo)
        with pytest.raises(SystemExit):
            cmd_delete([])
        # Branch should still exist in stack
        from gitstacker.store import load_state
        state = load_state()
        assert "branch-3" in state["stacks"]["test-stack"]["branches"]

    def test_delete_other_branch_allowed(self, stacked_repo):
        """Deleting a branch you're NOT on should work with dirty tree."""
        checkout("branch-1")
        self._make_dirty(stacked_repo)
        # This should NOT be blocked because we're not switching branches
        cmd_delete(["branch-3"])
        from gitstacker.store import load_state
        state = load_state()
        assert "branch-3" not in state["stacks"]["test-stack"]["branches"]


class TestCleanTreeAllowed:
    """Verify commands work normally with clean tree."""

    def test_navigate_clean(self, stacked_repo):
        checkout("branch-1")
        cmd_navigate("up", [])
        assert get_current_branch() == "branch-2"

    def test_create_clean(self, stacked_repo):
        checkout("branch-3")
        cmd_create(["branch-4"])
        assert get_current_branch() == "branch-4"
```

## Dependencies
- Depends on: task-05 (navigate already has check), task-02 (test infra)

## Acceptance Criteria
- [ ] `gs up/down/top/bottom` blocked with dirty tree
- [ ] `gs stack switch` blocked with dirty tree
- [ ] `gs sync` blocked with dirty tree
- [ ] `gs create` blocked with dirty tree
- [ ] `gs delete` blocked with dirty tree ONLY when deleting current branch
- [ ] `gs delete <other-branch>` works even with dirty tree (no branch switch needed)
- [ ] Error messages are clear and actionable ("Commit or stash your changes...")
- [ ] Commands that are blocked don't make any state changes
- [ ] `pytest tests/integration/test_dirty_tree.py -v` passes
- [ ] At least 8 test cases

## Notes
- `gs restack` already handles dirty trees by stashing — that behavior is intentionally different (it auto-stashes).
- The decision NOT to auto-stash for navigation/switch is deliberate: stash conflicts are confusing, and explicit is better.
- `gs delete <other-branch>` should still work with a dirty tree since no branch switch occurs.
- Consider the `--force` flag for power users who know what they're doing — out of scope for this task.
- `gs log` and `gs status` should NEVER block on dirty tree (they're read-only).
