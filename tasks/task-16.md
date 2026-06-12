# Task 16: E2E Full Workflow Tests

## Description
Write end-to-end tests that exercise the complete stacking lifecycle without mocks. These tests simulate a real developer workflow: init → create stack → create branches → commit → restack → navigate → delete. Also test multi-stack workflows and deep stacks.

## Files to Create/Modify
- `tests/e2e/__init__.py` — Ensure exists
- `tests/e2e/test_full_workflow.py` — Complete lifecycle tests

## Implementation Details

```python
"""
End-to-end workflow tests.
These test the full lifecycle of gitstacker commands working together.
No mocking — real git operations on real (temp) repos.
"""

import pytest
import subprocess
from gitstacker.commands.init import cmd_init
from gitstacker.commands.create import cmd_create
from gitstacker.commands.stack import cmd_stack
from gitstacker.commands.navigate import cmd_navigate
from gitstacker.commands.restack import cmd_restack
from gitstacker.commands.delete import cmd_delete
from gitstacker.commands.trunk import cmd_trunk
from gitstacker.git_ops import (
    get_current_branch, checkout, get_commit_count,
    get_commit_hash, branch_exists,
)
from gitstacker.store import load_state


def commit(repo, filename, content, message):
    (repo / filename).write_text(content)
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", message], cwd=repo, check=True)


class TestFullLifecycle:
    """Complete stacking lifecycle from init to cleanup."""

    def test_complete_workflow(self, git_repo):
        """init → stack → create 3 branches → commit → restack → verify."""
        # 1. Initialize
        cmd_init([])
        state = load_state()
        assert state["trunk"] == "main"

        # 2. Create stack
        cmd_stack(["new", "feature-auth"])
        state = load_state()
        assert state["current_stack"] == "feature-auth"

        # 3. Create branches with commits
        cmd_create(["auth-api"])
        commit(git_repo, "api.py", "def login(): pass", "Add login API")
        assert get_current_branch() == "auth-api"

        cmd_create(["auth-middleware"])
        commit(git_repo, "middleware.py", "def check_token(): pass", "Add auth middleware")
        assert get_current_branch() == "auth-middleware"

        cmd_create(["auth-ui"])
        commit(git_repo, "ui.py", "def login_page(): pass", "Add login page")
        assert get_current_branch() == "auth-ui"

        # 4. Verify stack structure
        state = load_state()
        stack = state["stacks"]["feature-auth"]
        assert stack["branches"] == ["auth-api", "auth-middleware", "auth-ui"]
        assert state["branches"]["auth-api"]["parent"] == "main"
        assert state["branches"]["auth-middleware"]["parent"] == "auth-api"
        assert state["branches"]["auth-ui"]["parent"] == "auth-middleware"

        # 5. Advance trunk
        checkout("main")
        commit(git_repo, "hotfix.py", "fix()", "Hotfix on trunk")

        # 6. Restack
        checkout("auth-api")
        cmd_restack([])

        # 7. Verify all branches updated
        # auth-api should have the hotfix in its history
        checkout("auth-api")
        result = subprocess.run(
            ["git", "log", "--oneline", "main..auth-api"],
            cwd=git_repo, capture_output=True, text=True
        )
        assert "login API" in result.stdout

        # 8. Navigate the stack
        cmd_navigate("bottom", [])
        assert get_current_branch() == "auth-api"
        cmd_navigate("up", [])
        assert get_current_branch() == "auth-middleware"
        cmd_navigate("top", [])
        assert get_current_branch() == "auth-ui"
        cmd_navigate("down", ["2"])
        assert get_current_branch() == "auth-api"

    def test_delete_from_middle_and_restack(self, git_repo):
        """Delete middle branch, then restack to verify chain integrity."""
        cmd_init([])
        cmd_stack(["new", "s"])

        cmd_create(["b1"])
        commit(git_repo, "b1.txt", "b1", "B1")
        cmd_create(["b2"])
        commit(git_repo, "b2.txt", "b2", "B2")
        cmd_create(["b3"])
        commit(git_repo, "b3.txt", "b3", "B3")

        # Delete middle
        cmd_delete(["b2"])
        state = load_state()
        assert state["branches"]["b3"]["parent"] == "b1"

        # Restack should work
        checkout("b1")
        cmd_restack([])
        state = load_state()
        assert "b2" not in state["stacks"]["s"]["branches"]
        assert state["stacks"]["s"]["branches"] == ["b1", "b3"]


class TestMultiStackWorkflow:
    """Working with multiple stacks."""

    def test_two_stacks_independent(self, git_repo):
        """Create 2 stacks, switch between them, verify independence."""
        cmd_init([])

        # Stack 1
        cmd_stack(["new", "feature-a"])
        cmd_create(["a1"])
        commit(git_repo, "a1.txt", "a1", "A1")
        cmd_create(["a2"])
        commit(git_repo, "a2.txt", "a2", "A2")

        # Stack 2
        checkout("main")
        cmd_stack(["new", "feature-b"])
        cmd_create(["b1"])
        commit(git_repo, "b1.txt", "b1", "B1")

        # Verify state
        state = load_state()
        assert len(state["stacks"]) == 2
        assert state["stacks"]["feature-a"]["branches"] == ["a1", "a2"]
        assert state["stacks"]["feature-b"]["branches"] == ["b1"]

        # Switch to stack A
        cmd_stack(["switch", "feature-a"])
        assert get_current_branch() == "a2"  # Goes to top of stack

        # Switch to stack B
        cmd_stack(["switch", "feature-b"])
        assert get_current_branch() == "b1"

    def test_restack_one_stack_doesnt_affect_other(self, git_repo):
        """Restacking one stack doesn't touch branches in another."""
        cmd_init([])

        cmd_stack(["new", "s1"])
        cmd_create(["s1-b1"])
        commit(git_repo, "s1.txt", "s1", "S1")

        checkout("main")
        cmd_stack(["new", "s2"])
        cmd_create(["s2-b1"])
        commit(git_repo, "s2.txt", "s2", "S2")

        # Advance trunk
        checkout("main")
        commit(git_repo, "trunk.txt", "trunk", "Trunk")

        # Restack s1 only
        cmd_stack(["switch", "s1"])
        s2_hash_before = get_commit_hash("s2-b1")
        cmd_restack([])
        s2_hash_after = get_commit_hash("s2-b1")

        # s2 should be unchanged
        assert s2_hash_before == s2_hash_after


class TestDeepStack:
    """Test with many branches (stress test)."""

    def test_ten_branch_stack(self, git_repo):
        """Stack with 10 branches works correctly."""
        cmd_init([])
        cmd_stack(["new", "deep"])

        for i in range(1, 11):
            cmd_create([f"layer-{i}"])
            commit(git_repo, f"layer-{i}.txt", f"content-{i}", f"Layer {i}")

        state = load_state()
        assert len(state["stacks"]["deep"]["branches"]) == 10

        # Navigate full stack
        cmd_navigate("bottom", [])
        assert get_current_branch() == "layer-1"
        cmd_navigate("top", [])
        assert get_current_branch() == "layer-10"
        cmd_navigate("down", ["5"])
        assert get_current_branch() == "layer-5"

    def test_deep_stack_restack(self, git_repo):
        """Restack 10-branch stack after trunk advance."""
        cmd_init([])
        cmd_stack(["new", "deep"])

        for i in range(1, 11):
            cmd_create([f"layer-{i}"])
            commit(git_repo, f"layer-{i}.txt", f"content-{i}", f"Layer {i}")

        # Advance trunk
        checkout("main")
        commit(git_repo, "new-trunk.txt", "new", "Trunk advance")

        # Restack all 10
        checkout("layer-1")
        cmd_restack([])

        # Verify chain is intact
        for i in range(1, 11):
            assert get_commit_count(f"layer-{i-1}" if i > 1 else "main", f"layer-{i}") == 1


class TestBranchNameEdgeCases:
    """Test with unusual branch names."""

    def test_slash_names(self, git_repo):
        """Branch names with slashes work."""
        cmd_init([])
        cmd_stack(["new", "s"])
        cmd_create(["feat/auth/login"])
        commit(git_repo, "login.txt", "x", "Add login")
        cmd_create(["feat/auth/signup"])
        commit(git_repo, "signup.txt", "x", "Add signup")

        state = load_state()
        assert "feat/auth/login" in state["stacks"]["s"]["branches"]

        cmd_navigate("bottom", [])
        assert get_current_branch() == "feat/auth/login"

    def test_hyphenated_names(self, git_repo):
        """Branch names with many hyphens work."""
        cmd_init([])
        cmd_stack(["new", "s"])
        cmd_create(["my-very-long-branch-name-with-many-hyphens"])
        assert get_current_branch() == "my-very-long-branch-name-with-many-hyphens"
```

## Dependencies
- Depends on: task-05 (navigation fixes), task-08 (restack fixes), task-10 (delete fix)

## Acceptance Criteria
- [ ] `pytest tests/e2e/test_full_workflow.py -v` passes all tests
- [ ] Complete lifecycle tested: init → stack → create → commit → restack → navigate
- [ ] Multi-stack workflow tested: create 2 stacks, switch, verify independence
- [ ] Deep stack (10 branches) tested for create, navigate, and restack
- [ ] Delete-from-middle + restack tested
- [ ] Branch names with slashes and hyphens tested
- [ ] All tests use real git repos (no mocking)
- [ ] Tests run in under 30 seconds total
- [ ] At least 8 test cases

## Notes
- These tests are intentionally longer than unit/integration tests — they test the full flow.
- Deep stack tests may be slower due to 10 branch creations + rebases.
- Branch names with slashes are common in real workflows (`feat/`, `fix/`, etc.).
- The multi-stack test verifies that restacking one stack doesn't affect another.
