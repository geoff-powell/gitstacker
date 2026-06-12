"""
Unit tests for gitstacker/store.py — state persistence and stack/branch operations.
"""

import json
import os
from unittest.mock import patch

import pytest

from gitstacker.store import (
    add_branch_to_stack,
    create_stack,
    delete_stack,
    get_branch_position,
    get_child_branches,
    get_current_stack,
    get_parent_branch,
    init_state,
    is_initialized,
    load_state,
    remove_branch_from_stack,
    save_state,
)


class TestSaveState:
    """Tests for save_state() — atomic JSON persistence."""

    def test_save_creates_valid_json(self, initialized_repo):
        """save_state writes parseable JSON file."""
        state = load_state()
        state["trunk"] = "develop"
        save_state(state)

        state_path = initialized_repo / ".git" / "gitstacker" / "state.json"
        with open(state_path, "r") as f:
            loaded = json.load(f)
        assert loaded["trunk"] == "develop"

    def test_save_is_atomic_no_partial_writes(self, initialized_repo):
        """Mock os.replace to raise; verify original untouched."""
        # Save initial state
        state = load_state()
        original_trunk = state["trunk"]
        save_state(state)

        # Attempt to save new state with mocked os.replace raising
        new_state = state.copy()
        new_state["trunk"] = "should-not-persist"

        with patch("gitstacker.store.os.replace", side_effect=OSError("disk full")):
            with pytest.raises(RuntimeError, match="Failed to save state"):
                save_state(new_state)

        # Original file should be untouched
        reloaded = load_state()
        assert reloaded["trunk"] == original_trunk

    def test_save_creates_no_tmp_file_on_success(self, initialized_repo):
        """No .tmp file left after successful save."""
        state = load_state()
        save_state(state)

        state_path = initialized_repo / ".git" / "gitstacker" / "state.json"
        tmp_path = str(state_path) + ".tmp"
        assert not os.path.exists(tmp_path)


class TestLoadState:
    """Tests for load_state() — reading and validating state from disk."""

    def test_load_returns_complete_state(self, initialized_repo):
        """Returns dict with all required keys."""
        state = load_state()
        assert "trunk" in state
        assert "stacks" in state
        assert "branches" in state
        assert "current_stack" in state
        assert "version" in state

    def test_load_fills_missing_keys(self, initialized_repo):
        """Write state.json missing 'branches' key; load fills default."""
        state_path = initialized_repo / ".git" / "gitstacker" / "state.json"
        # Write state without 'branches' key
        incomplete_state = {"trunk": "main", "stacks": {}, "current_stack": None, "version": 1}
        with open(state_path, "w") as f:
            json.dump(incomplete_state, f)

        state = load_state()
        assert "branches" in state
        assert state["branches"] == {}

    def test_load_raises_on_uninitialized(self, git_repo):
        """Raises RuntimeError if not initialized."""
        with pytest.raises(RuntimeError, match="not initialized"):
            load_state()

    def test_load_handles_corrupt_json(self, initialized_repo):
        """Write garbage to state.json; verify error message mentions corruption."""
        state_path = initialized_repo / ".git" / "gitstacker" / "state.json"
        # Remove any backup so recovery doesn't kick in
        bak_path = str(state_path) + ".bak"
        if os.path.exists(bak_path):
            os.unlink(bak_path)

        with open(state_path, "w") as f:
            f.write("{{{not valid json!!!")

        with pytest.raises(RuntimeError, match="corrupted"):
            load_state()

    def test_load_recovers_from_backup(self, initialized_repo):
        """Corrupt main file but have valid .bak; verify recovery works."""
        state_path = initialized_repo / ".git" / "gitstacker" / "state.json"
        bak_path = str(state_path) + ".bak"

        # Create a valid backup
        valid_state = {"trunk": "main", "stacks": {}, "branches": {}, "current_stack": None, "version": 1}
        with open(bak_path, "w") as f:
            json.dump(valid_state, f)

        # Corrupt main state file
        with open(state_path, "w") as f:
            f.write("not valid json at all!")

        # load_state should recover from backup
        state = load_state()
        assert state["trunk"] == "main"
        assert isinstance(state["stacks"], dict)

    def test_load_fixes_wrong_types(self, initialized_repo):
        """Write state where 'stacks' is a list; verify corrected to {}."""
        state_path = initialized_repo / ".git" / "gitstacker" / "state.json"
        wrong_type_state = {
            "trunk": "main",
            "stacks": ["not", "a", "dict"],
            "branches": {},
            "current_stack": None,
            "version": 1,
        }
        with open(state_path, "w") as f:
            json.dump(wrong_type_state, f)

        state = load_state()
        assert isinstance(state["stacks"], dict)
        assert state["stacks"] == {}


class TestInitState:
    """Tests for init_state() — creating fresh gitstacker state."""

    def test_init_creates_state_file(self, git_repo):
        """Verify .git/gitstacker/state.json exists after init."""
        init_state("main")
        state_path = git_repo / ".git" / "gitstacker" / "state.json"
        assert state_path.exists()

    def test_init_sets_trunk(self, git_repo):
        """Verify trunk is set to provided value."""
        state = init_state("develop")
        assert state["trunk"] == "develop"

    def test_init_state_structure(self, git_repo):
        """Returned state has correct types for all keys."""
        state = init_state("main")
        assert isinstance(state["trunk"], str)
        assert isinstance(state["stacks"], dict)
        assert isinstance(state["branches"], dict)
        assert state["current_stack"] is None
        assert isinstance(state["version"], int)


class TestStackOperations:
    """Tests for create_stack() and delete_stack()."""

    def test_create_stack(self, initialized_repo):
        """Creates stack with name, trunk, empty branches list."""
        state = load_state()
        stack = create_stack(state, "my-stack", "main")

        assert stack["name"] == "my-stack"
        assert stack["trunk"] == "main"
        assert stack["branches"] == []
        assert "my-stack" in state["stacks"]

    def test_create_duplicate_stack_raises(self, initialized_repo):
        """RuntimeError on duplicate name."""
        state = load_state()
        create_stack(state, "my-stack")

        with pytest.raises(RuntimeError, match="already exists"):
            create_stack(state, "my-stack")

    def test_delete_stack_removes_branches(self, stacked_repo):
        """Branch metadata also removed when stack is deleted."""
        state = load_state()
        assert "branch-1" in state["branches"]
        assert "branch-2" in state["branches"]
        assert "branch-3" in state["branches"]

        delete_stack(state, "test-stack")

        assert "branch-1" not in state["branches"]
        assert "branch-2" not in state["branches"]
        assert "branch-3" not in state["branches"]

    def test_delete_nonexistent_stack_raises(self, initialized_repo):
        """RuntimeError for unknown name."""
        state = load_state()
        with pytest.raises(RuntimeError, match="not found"):
            delete_stack(state, "nonexistent-stack")

    def test_delete_stack_clears_current(self, stacked_repo):
        """If deleted stack was current, current_stack becomes None."""
        state = load_state()
        assert state["current_stack"] == "test-stack"

        delete_stack(state, "test-stack")
        assert state["current_stack"] is None


class TestBranchOperations:
    """Tests for add/remove branch operations and query helpers."""

    def test_add_branch_to_stack(self, initialized_repo):
        """Appends to branches list and creates metadata dict."""
        state = load_state()
        create_stack(state, "my-stack", "main")

        add_branch_to_stack(state, "my-stack", "feature-1", "main")

        assert "feature-1" in state["stacks"]["my-stack"]["branches"]
        assert "feature-1" in state["branches"]
        assert state["branches"]["feature-1"]["parent"] == "main"
        assert state["branches"]["feature-1"]["name"] == "feature-1"
        assert state["branches"]["feature-1"]["pr_number"] is None
        assert state["branches"]["feature-1"]["pr_url"] is None
        assert state["branches"]["feature-1"]["commit_base"] is None

    def test_remove_branch_updates_child_parent(self, stacked_repo):
        """Middle branch removal reparents child."""
        state = load_state()
        # branch-2 is between branch-1 and branch-3
        # Removing branch-2 should make branch-3's parent become branch-1
        remove_branch_from_stack(state, "branch-2")

        assert "branch-2" not in state["branches"]
        assert "branch-2" not in state["stacks"]["test-stack"]["branches"]
        # branch-3's parent should now be branch-1
        assert state["branches"]["branch-3"]["parent"] == "branch-1"

    def test_get_parent_of_first_branch_is_trunk(self, stacked_repo):
        """First branch parent is stack trunk."""
        state = load_state()
        stack = state["stacks"]["test-stack"]
        parent = get_parent_branch(state, stack, "branch-1")
        assert parent == "main"

    def test_get_parent_of_nth_branch(self, stacked_repo):
        """Second branch parent is first branch."""
        state = load_state()
        stack = state["stacks"]["test-stack"]
        parent = get_parent_branch(state, stack, "branch-2")
        assert parent == "branch-1"

    def test_get_child_branches(self, stacked_repo):
        """Returns all branches after the given one."""
        state = load_state()
        stack = state["stacks"]["test-stack"]
        children = get_child_branches(stack, "branch-1")
        assert children == ["branch-2", "branch-3"]

    def test_get_child_branches_of_last(self, stacked_repo):
        """Returns empty list for last branch."""
        state = load_state()
        stack = state["stacks"]["test-stack"]
        children = get_child_branches(stack, "branch-3")
        assert children == []

    def test_get_branch_position(self, stacked_repo):
        """Returns correct 0-indexed position."""
        state = load_state()
        stack = state["stacks"]["test-stack"]
        assert get_branch_position(stack, "branch-1") == 0
        assert get_branch_position(stack, "branch-2") == 1
        assert get_branch_position(stack, "branch-3") == 2

    def test_get_branch_position_missing(self, stacked_repo):
        """Returns -1 for nonexistent branch."""
        state = load_state()
        stack = state["stacks"]["test-stack"]
        assert get_branch_position(stack, "nonexistent") == -1


class TestGetCurrentStack:
    """Tests for get_current_stack() — finding stack by branch."""

    def test_find_stack_by_branch(self, stacked_repo):
        """Returns the stack dict containing the branch."""
        state = load_state()
        stack = get_current_stack(state, "branch-2")
        assert stack is not None
        assert stack["name"] == "test-stack"
        assert "branch-2" in stack["branches"]

    def test_returns_none_for_unknown_branch(self, stacked_repo):
        """Returns None for branch not in any stack."""
        state = load_state()
        result = get_current_stack(state, "unknown-branch")
        assert result is None
