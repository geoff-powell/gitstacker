# Task 03: Unit Tests for store.py

## Description
Write comprehensive unit tests for `gitstacker/store.py` covering state CRUD operations, validation, corruption recovery, and edge cases. These tests verify the fixes from Task 01 work correctly and prevent regressions.

## Files to Create/Modify
- `tests/unit/__init__.py` — Ensure exists
- `tests/unit/test_store.py` — Unit tests for all store.py functions

## Implementation Details

### Test cases to cover:

```python
import pytest
import json
import os
from unittest.mock import patch

class TestSaveState:
    """Tests for atomic write behavior."""

    def test_save_creates_valid_json(self, initialized_repo):
        """save_state writes parseable JSON."""

    def test_save_is_atomic_no_partial_writes(self, initialized_repo):
        """If write fails mid-way, original state.json is intact."""

    def test_save_creates_no_tmp_file_on_success(self, initialized_repo):
        """Temp file is cleaned up after successful save."""


class TestLoadState:
    """Tests for load and validation."""

    def test_load_returns_complete_state(self, initialized_repo):
        """load_state returns dict with all required keys."""

    def test_load_fills_missing_keys(self, initialized_repo):
        """If state.json is missing 'branches' key, it's filled with default."""

    def test_load_raises_on_uninitialized(self, git_repo):
        """load_state raises RuntimeError if not initialized."""

    def test_load_handles_corrupt_json(self, initialized_repo):
        """If state.json has invalid JSON, attempt .bak recovery or clear error."""

    def test_load_fixes_wrong_types(self, initialized_repo):
        """If 'stacks' is somehow a list, it's corrected to {}."""


class TestInitState:
    """Tests for initialization."""

    def test_init_creates_state_file(self, git_repo):
        """init_state creates .git/gitstacker/state.json."""

    def test_init_sets_trunk(self, git_repo):
        """init_state stores the provided trunk name."""

    def test_init_state_structure(self, git_repo):
        """Returned state has all required keys with correct types."""


class TestStackOperations:
    """Tests for stack CRUD."""

    def test_create_stack(self, initialized_repo):
        """create_stack adds a new stack to state."""

    def test_create_duplicate_stack_raises(self, initialized_repo):
        """create_stack raises if name already exists."""

    def test_delete_stack_removes_branches(self, stacked_repo):
        """delete_stack removes branch metadata too."""

    def test_delete_nonexistent_stack_raises(self, initialized_repo):
        """delete_stack raises for unknown name."""


class TestBranchOperations:
    """Tests for branch management within stacks."""

    def test_add_branch_to_stack(self, initialized_repo):
        """add_branch_to_stack appends to branches list and creates metadata."""

    def test_remove_branch_updates_child_parent(self, stacked_repo):
        """Removing middle branch re-parents children."""

    def test_get_parent_of_first_branch_is_trunk(self, stacked_repo):
        """First branch's parent is trunk."""

    def test_get_parent_of_nth_branch(self, stacked_repo):
        """Nth branch's parent is N-1 branch."""

    def test_get_child_branches(self, stacked_repo):
        """get_child_branches returns all branches above."""

    def test_get_branch_position(self, stacked_repo):
        """get_branch_position returns correct 0-indexed position."""

    def test_get_branch_position_missing(self, stacked_repo):
        """get_branch_position returns -1 for missing branch."""


class TestGetCurrentStack:
    """Tests for finding the active stack."""

    def test_find_stack_by_branch(self, stacked_repo):
        """get_current_stack finds the stack containing a branch."""

    def test_returns_none_for_unknown_branch(self, stacked_repo):
        """get_current_stack returns None for non-stacked branch."""
```

### Key patterns:
- Use `initialized_repo` fixture for tests that need state.json to exist
- Use `stacked_repo` for tests that need branches already in a stack
- Directly manipulate `.git/gitstacker/state.json` to test corruption scenarios
- Use `monkeypatch` to simulate filesystem errors for atomic write tests

## Dependencies
- Depends on: task-01 (store.py fixes), task-02 (test infrastructure)

## Acceptance Criteria
- [ ] `pytest tests/unit/test_store.py -v` passes all tests
- [ ] Tests cover: init_state, load_state, save_state, create_stack, delete_stack
- [ ] Tests cover: add_branch_to_stack, remove_branch_from_stack, get_parent_branch
- [ ] Tests cover: get_current_stack, get_branch_position, get_child_branches
- [ ] Corruption scenarios tested: missing keys, invalid JSON, wrong types
- [ ] Atomic write tested: no partial files left on success
- [ ] At least 15 test cases

## Notes
- For the atomic write failure test, you can mock `os.replace` to raise `OSError` and verify the original file is untouched.
- For corrupt JSON tests, write garbage bytes directly to the state file path.
- The `stacked_repo` fixture already creates 3 branches, so you can test position/parent logic without setup boilerplate.
