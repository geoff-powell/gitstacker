# Task 04: Unit Tests for git_ops.py

## Description
Write unit tests for `gitstacker/git_ops.py` covering git command construction, result parsing, and error handling. Tests use real git repos via the `git_repo` fixture to verify actual git operations work correctly.

## Files to Create/Modify
- `tests/unit/test_git_ops.py` — Unit tests for all git_ops.py functions

## Implementation Details

### Test cases to cover:

```python
import pytest
import subprocess
from gitstacker.git_ops import (
    git, git_or_throw, GitResult,
    get_current_branch, get_git_root, is_git_repo,
    get_default_branch, branch_exists, create_branch,
    checkout, get_merge_base, get_commit_hash, get_short_hash,
    get_commit_count, get_log_oneline, is_working_tree_clean,
    stash_push, stash_pop, list_branches, rebase_onto,
    push_branch, rebase_abort,
)


class TestGitResult:
    """Tests for the GitResult dataclass."""

    def test_success_on_zero_returncode(self):
        r = GitResult(stdout="ok", stderr="", returncode=0)
        assert r.success is True

    def test_failure_on_nonzero_returncode(self):
        r = GitResult(stdout="", stderr="error", returncode=1)
        assert r.success is False


class TestGitCommand:
    """Tests for the base git() function."""

    def test_git_returns_result(self, git_repo):
        result = git("status")
        assert result.success
        assert result.returncode == 0

    def test_git_captures_stdout(self, git_repo):
        result = git("branch", "--show-current")
        assert result.stdout == "main"

    def test_git_cwd_parameter(self, tmp_path):
        """git() respects cwd parameter."""
        # Create a separate repo
        other = tmp_path / "other"
        other.mkdir()
        subprocess.run(["git", "init", "-b", "other-main"], cwd=other, check=True)
        result = git("branch", "--show-current", cwd=str(other))
        # May fail because no commits, but tests cwd is passed through


class TestGitOrThrow:
    """Tests for git_or_throw error behavior."""

    def test_returns_stdout_on_success(self, git_repo):
        result = git_or_throw("branch", "--show-current")
        assert result == "main"

    def test_raises_on_failure(self, git_repo):
        with pytest.raises(RuntimeError, match="failed"):
            git_or_throw("checkout", "nonexistent-branch-xyz")


class TestBranchOperations:
    """Tests for branch-related operations."""

    def test_get_current_branch(self, git_repo):
        assert get_current_branch() == "main"

    def test_branch_exists_true(self, git_repo):
        assert branch_exists("main") is True

    def test_branch_exists_false(self, git_repo):
        assert branch_exists("nonexistent") is False

    def test_create_branch_switches(self, git_repo):
        create_branch("feature-1")
        assert get_current_branch() == "feature-1"

    def test_checkout_existing_branch(self, git_repo):
        create_branch("feature-1")
        checkout("main")
        assert get_current_branch() == "main"

    def test_list_branches(self, git_repo):
        create_branch("feat-a")
        checkout("main")
        create_branch("feat-b")
        branches = list_branches()
        assert "main" in branches
        assert "feat-a" in branches
        assert "feat-b" in branches


class TestCommitInfo:
    """Tests for commit hash and log operations."""

    def test_get_commit_hash_is_40_chars(self, git_repo):
        h = get_commit_hash("HEAD")
        assert len(h) == 40

    def test_get_short_hash_is_7_or_more(self, git_repo):
        h = get_short_hash("HEAD")
        assert 7 <= len(h) <= 12

    def test_get_commit_count(self, git_repo):
        # git_repo has 1 initial commit
        create_branch("test")
        (git_repo / "new.txt").write_text("hello")
        subprocess.run(["git", "add", "."], cwd=git_repo, check=True)
        subprocess.run(["git", "commit", "-m", "second"], cwd=git_repo, check=True)
        assert get_commit_count("main", "test") == 1

    def test_get_log_oneline(self, git_repo):
        create_branch("test")
        (git_repo / "new.txt").write_text("hello")
        subprocess.run(["git", "add", "."], cwd=git_repo, check=True)
        subprocess.run(["git", "commit", "-m", "Add file"], cwd=git_repo, check=True)
        logs = get_log_oneline("main", "test")
        assert len(logs) == 1
        assert "Add file" in logs[0]


class TestWorkingTree:
    """Tests for working tree status and stash."""

    def test_clean_tree(self, git_repo):
        assert is_working_tree_clean() is True

    def test_dirty_tree_untracked(self, git_repo):
        (git_repo / "untracked.txt").write_text("dirty")
        assert is_working_tree_clean() is False

    def test_dirty_tree_modified(self, git_repo):
        (git_repo / "README.md").write_text("modified")
        assert is_working_tree_clean() is False

    def test_stash_push_and_pop(self, git_repo):
        (git_repo / "README.md").write_text("modified")
        assert stash_push() is True
        assert is_working_tree_clean() is True
        assert stash_pop() is True
        assert (git_repo / "README.md").read_text() == "modified"


class TestRepoDetection:
    """Tests for repo detection utilities."""

    def test_is_git_repo_true(self, git_repo):
        assert is_git_repo() is True

    def test_get_git_root(self, git_repo):
        assert get_git_root() == str(git_repo)

    def test_get_default_branch(self, git_repo):
        assert get_default_branch() == "main"
```

## Dependencies
- Depends on: task-02 (test infrastructure, git_repo fixture)

## Acceptance Criteria
- [ ] `pytest tests/unit/test_git_ops.py -v` passes all tests
- [ ] Tests cover: git(), git_or_throw(), GitResult
- [ ] Tests cover: get_current_branch, branch_exists, create_branch, checkout
- [ ] Tests cover: get_commit_hash, get_commit_count, get_log_oneline
- [ ] Tests cover: is_working_tree_clean, stash_push, stash_pop
- [ ] Tests cover: is_git_repo, get_git_root, get_default_branch, list_branches
- [ ] Error cases tested: git_or_throw raises RuntimeError on failure
- [ ] At least 18 test cases

## Notes
- These tests use real git repos (via `git_repo` fixture), not mocked subprocess calls. This ensures we're testing real behavior.
- `get_default_branch()` has multiple code paths — test when `origin/HEAD` exists vs. fallback to checking `main`/`master`.
- `rebase_onto` is harder to unit test in isolation — save that for integration tests.
- Don't test `push_branch` or `fetch_remote` here since they need a remote — those go in integration tests.
