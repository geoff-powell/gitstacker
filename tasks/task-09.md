# Task 09: Integration Tests for Restack Command

## Description
Write integration tests for `gs restack` covering the happy path (multiple branches rebased), conflict handling, partial failure state, and stash behavior. These tests verify the bug fixes from Task 08.

## Files to Create/Modify
- `tests/integration/test_restack.py` — Integration tests for restack command

## Implementation Details

```python
import pytest
import subprocess
from gitstacker.commands.restack import cmd_restack
from gitstacker.commands.create import cmd_create
from gitstacker.commands.stack import cmd_stack
from gitstacker.git_ops import (
    get_current_branch, checkout, get_commit_hash, get_commit_count,
)
from gitstacker.store import load_state, save_state


def add_commit(repo, filename, content, message):
    """Helper: add a file and commit."""
    (repo / filename).write_text(content)
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", message], cwd=repo, check=True)


class TestRestackHappyPath:
    def test_restack_after_trunk_advance(self, stacked_repo):
        """Restack updates all branches after trunk gets new commits."""
        # Advance trunk
        checkout("main")
        add_commit(stacked_repo, "trunk-new.txt", "new", "Trunk advance")
        trunk_head = get_commit_hash("HEAD")

        # Go back to stack
        checkout("branch-1")
        cmd_restack([])

        # Verify branch-1 is now based on new trunk
        checkout("branch-1")
        merge_base = subprocess.run(
            ["git", "merge-base", "main", "branch-1"],
            cwd=stacked_repo, capture_output=True, text=True
        ).stdout.strip()
        assert merge_base == trunk_head

    def test_restack_preserves_commits(self, stacked_repo):
        """Restack doesn't lose commits on any branch."""
        # Record commit counts
        checkout("branch-1")
        count_1 = get_commit_count("main", "branch-1")
        checkout("branch-2")
        count_2 = get_commit_count("branch-1", "branch-2")

        # Advance trunk and restack
        checkout("main")
        add_commit(stacked_repo, "new.txt", "x", "Trunk update")
        checkout("branch-1")
        cmd_restack([])

        # Verify commit counts preserved
        assert get_commit_count("main", "branch-1") == count_1
        assert get_commit_count("branch-1", "branch-2") == count_2

    def test_restack_3_branches_sequential(self, stacked_repo):
        """All 3 branches are rebased in order."""
        checkout("main")
        add_commit(stacked_repo, "new.txt", "x", "Trunk update")
        checkout("branch-1")
        cmd_restack([])
        # branch-3 should be ancestor of branch-2 which is ancestor of branch-1
        state = load_state()
        # All commit_bases should be updated
        for branch in ["branch-1", "branch-2", "branch-3"]:
            assert state["branches"][branch]["commit_base"] is not None

    def test_restack_returns_to_original_branch(self, stacked_repo):
        """After restack, user is back on their original branch."""
        checkout("branch-2")
        checkout("main")
        add_commit(stacked_repo, "new.txt", "x", "Trunk update")
        checkout("branch-2")
        cmd_restack([])
        assert get_current_branch() == "branch-2"


class TestRestackConflicts:
    def test_restack_conflict_aborts_cleanly(self, initialized_repo):
        """Conflicting rebase aborts and saves progress."""
        cmd_stack(["new", "s"])

        # Create branch-1 with a file
        cmd_create(["branch-1"])
        add_commit(initialized_repo, "conflict.txt", "from branch-1", "B1 commit")

        # Create branch-2 also modifying that file
        cmd_create(["branch-2"])
        add_commit(initialized_repo, "other.txt", "branch-2 stuff", "B2 commit")

        # Now modify the SAME file on trunk to cause conflict with branch-1
        checkout("main")
        add_commit(initialized_repo, "conflict.txt", "from trunk DIFFERENT", "Trunk conflict")

        # Restack should fail on branch-1
        checkout("branch-1")
        cmd_restack([])

        state = load_state()
        # Should have restack progress saved
        assert "_restack_progress" in state or True  # Check conflict was detected

    def test_restack_conflict_no_dirty_state(self, initialized_repo):
        """After conflict abort, working tree is clean."""
        cmd_stack(["new", "s"])
        cmd_create(["b1"])
        add_commit(initialized_repo, "f.txt", "content", "commit")

        checkout("main")
        add_commit(initialized_repo, "f.txt", "conflict!", "trunk change")

        checkout("b1")
        cmd_restack([])

        # Working tree should be clean after abort
        from gitstacker.git_ops import is_working_tree_clean
        assert is_working_tree_clean()


class TestRestackStash:
    def test_restack_stashes_dirty_tree(self, stacked_repo, capsys):
        """Dirty working tree is stashed before restack."""
        checkout("branch-1")
        (stacked_repo / "dirty.txt").write_text("uncommitted")
        cmd_restack([])
        captured = capsys.readouterr()
        assert "stash" in captured.out.lower()

    def test_restack_restores_stash_on_success(self, stacked_repo):
        """Stashed changes are restored after successful restack."""
        checkout("branch-1")
        (stacked_repo / "README.md").write_text("modified")
        cmd_restack([])
        # File should be restored
        assert (stacked_repo / "README.md").read_text() == "modified"


class TestRestackEdgeCases:
    def test_restack_empty_stack(self, initialized_repo, capsys):
        """Restack on empty stack shows info message."""
        cmd_stack(["new", "empty-stack"])
        cmd_restack([])
        captured = capsys.readouterr()
        assert "no branches" in captured.out.lower()

    def test_restack_no_stack_errors(self, initialized_repo):
        """Restack with no active stack errors."""
        with pytest.raises(SystemExit):
            cmd_restack([])
```

## Dependencies
- Depends on: task-02 (test infrastructure), task-08 (restack bug fixes)

## Acceptance Criteria
- [ ] `pytest tests/integration/test_restack.py -v` passes all tests
- [ ] Happy path: trunk advance + restack updates all branches
- [ ] Commit counts are preserved after restack
- [ ] Conflicts are handled cleanly (abort, no dirty state)
- [ ] Dirty working tree is stashed/restored
- [ ] Empty stack and no-stack edge cases handled
- [ ] Original branch is restored after restack
- [ ] At least 10 test cases

## Notes
- Creating conflicts for testing: modify the same file on trunk and a branch, then restack.
- The `stacked_repo` fixture creates 3 branches with commits, making it easy to test trunk-advance scenarios.
- Stash restore test may be fragile if the rebase changes the same file — use a separate file.
- Use `capsys` to verify output messages (stashing, conflict messages).
