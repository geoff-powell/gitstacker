"""Tests for dirty working tree blocking across all commands."""

import pytest
from gitstacker.commands.navigate import cmd_navigate
from gitstacker.commands.stack import cmd_stack
from gitstacker.commands.sync import cmd_sync
from gitstacker.commands.delete import cmd_delete
from gitstacker.commands.create import cmd_create
from gitstacker.git_ops import get_current_branch, checkout, branch_exists
from gitstacker.store import load_state, save_state


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
        # Create second stack to switch to
        state = load_state()
        state["stacks"]["other-stack"] = {
            "name": "other-stack",
            "trunk": "main",
            "branches": [],
        }
        save_state(state)

        checkout("branch-1")
        self._make_dirty(stacked_repo)
        with pytest.raises(SystemExit):
            cmd_stack(["switch", "other-stack"])
        assert get_current_branch() == "branch-1"

    def test_create_blocked(self, stacked_repo):
        checkout("branch-1")
        self._make_dirty(stacked_repo)
        with pytest.raises(SystemExit):
            cmd_create(["new-branch"])
        # Branch should not have been created
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
        state = load_state()
        assert "branch-3" in state["stacks"]["test-stack"]["branches"]

    def test_delete_other_branch_allowed(self, stacked_repo):
        """Deleting a branch you're NOT on should work with dirty tree."""
        checkout("branch-1")
        self._make_dirty(stacked_repo)
        # This should NOT be blocked because we're not switching branches
        cmd_delete(["branch-3"])
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
