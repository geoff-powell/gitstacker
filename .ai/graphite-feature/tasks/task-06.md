# Task 06: Integration Tests for Init and Create Commands

## Description
Write integration tests for `gs init` and `gs create` commands using real git repos. Test various scenarios including fresh repos, already-initialized repos, non-git directories, branch creation at various positions, and error cases.

## Files to Create/Modify
- `tests/integration/__init__.py` — Ensure exists
- `tests/integration/test_init.py` — Integration tests for `gs init`
- `tests/integration/test_create.py` — Integration tests for `gs create`

## Implementation Details

### test_init.py

```python
import pytest
import os
from gitstacker.commands.init import cmd_init
from gitstacker.store import load_state, is_initialized


class TestInit:
    def test_init_fresh_repo(self, git_repo):
        """gs init in a fresh repo creates state.json."""
        cmd_init([])
        assert is_initialized()
        state = load_state()
        assert state["trunk"] == "main"
        assert state["stacks"] == {}
        assert state["branches"] == {}

    def test_init_with_explicit_trunk(self, git_repo):
        """gs init <branch> sets custom trunk."""
        cmd_init(["main"])
        state = load_state()
        assert state["trunk"] == "main"

    def test_init_already_initialized(self, initialized_repo, capsys):
        """gs init when already initialized prints info, doesn't error."""
        cmd_init([])
        captured = capsys.readouterr()
        assert "already initialized" in captured.out.lower()

    def test_init_not_git_repo(self, tmp_path, monkeypatch):
        """gs init outside git repo exits with error."""
        monkeypatch.chdir(tmp_path)
        with pytest.raises(SystemExit):
            cmd_init([])

    def test_init_creates_data_directory(self, git_repo):
        """gs init creates .git/gitstacker/ directory."""
        cmd_init([])
        data_dir = git_repo / ".git" / "gitstacker"
        assert data_dir.exists()
        assert (data_dir / "state.json").exists()
```

### test_create.py

```python
import pytest
import subprocess
from gitstacker.commands.create import cmd_create
from gitstacker.commands.stack import cmd_stack
from gitstacker.store import load_state
from gitstacker.git_ops import get_current_branch


class TestCreate:
    def test_create_first_branch(self, initialized_repo):
        """Create first branch on a new stack."""
        cmd_stack(["new", "my-stack"])
        cmd_create(["feature-1"])
        assert get_current_branch() == "feature-1"
        state = load_state()
        assert "feature-1" in state["stacks"]["my-stack"]["branches"]
        assert state["branches"]["feature-1"]["parent"] == "main"

    def test_create_second_branch(self, initialized_repo):
        """Second branch parents to first branch."""
        cmd_stack(["new", "my-stack"])
        cmd_create(["branch-a"])
        # Add a commit so branches diverge
        (initialized_repo / "a.txt").write_text("a")
        subprocess.run(["git", "add", "."], cwd=initialized_repo, check=True)
        subprocess.run(["git", "commit", "-m", "commit on a"], cwd=initialized_repo, check=True)
        cmd_create(["branch-b"])
        state = load_state()
        assert state["branches"]["branch-b"]["parent"] == "branch-a"

    def test_create_from_trunk(self, initialized_repo):
        """Create branch while on trunk uses trunk as parent."""
        cmd_stack(["new", "my-stack"])
        cmd_create(["first-branch"])
        state = load_state()
        assert state["branches"]["first-branch"]["parent"] == "main"

    def test_create_duplicate_branch_errors(self, initialized_repo):
        """Creating branch with existing name fails."""
        cmd_stack(["new", "s"])
        cmd_create(["dupe"])
        with pytest.raises(SystemExit):
            cmd_create(["dupe"])

    def test_create_no_stack_errors(self, initialized_repo):
        """Create without active stack fails."""
        with pytest.raises(SystemExit):
            cmd_create(["orphan"])

    def test_create_no_name_errors(self, initialized_repo):
        """Create without branch name fails."""
        cmd_stack(["new", "s"])
        with pytest.raises(SystemExit):
            cmd_create([])

    def test_create_records_commit_base(self, initialized_repo):
        """commit_base is recorded for restack use."""
        cmd_stack(["new", "s"])
        cmd_create(["br"])
        state = load_state()
        assert state["branches"]["br"]["commit_base"] is not None
        assert len(state["branches"]["br"]["commit_base"]) == 40

    def test_create_branch_with_slashes(self, initialized_repo):
        """Branch names with slashes (feat/auth) work."""
        cmd_stack(["new", "s"])
        cmd_create(["feat/auth"])
        assert get_current_branch() == "feat/auth"
```

## Dependencies
- Depends on: task-02 (test infrastructure), task-01 (store fixes)

## Acceptance Criteria
- [ ] `pytest tests/integration/test_init.py -v` passes all tests
- [ ] `pytest tests/integration/test_create.py -v` passes all tests
- [ ] Init tested: fresh repo, explicit trunk, already initialized, non-git dir
- [ ] Create tested: first branch, second branch, from trunk, duplicate, no stack, no name
- [ ] Branch names with slashes (e.g., `feat/auth`) work correctly
- [ ] commit_base is correctly recorded on creation
- [ ] At least 12 test cases total

## Notes
- Use `capsys` fixture to check printed output messages.
- `cmd_init`, `cmd_create`, etc. are called directly (not via subprocess) for speed.
- The `initialized_repo` fixture provides a repo with `gs init` already done.
- Some tests need a commit on each branch to verify parent relationships properly.
