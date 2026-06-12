"""
Unit tests for gitstacker/git_ops.py — git command execution and branch operations.
"""

import subprocess

import pytest

from gitstacker.git_ops import (
    GitResult,
    branch_exists,
    checkout,
    create_branch,
    get_commit_count,
    get_commit_hash,
    get_current_branch,
    get_default_branch,
    get_git_root,
    get_log_oneline,
    get_short_hash,
    git,
    git_or_throw,
    is_git_repo,
    is_working_tree_clean,
    list_branches,
    stash_pop,
    stash_push,
)


class TestGitResult:
    """Tests for GitResult dataclass."""

    def test_success_on_zero_returncode(self):
        """GitResult with returncode=0 reports success."""
        result = GitResult(stdout="", stderr="", returncode=0)
        assert result.success is True

    def test_failure_on_nonzero_returncode(self):
        """GitResult with returncode=1 reports failure."""
        result = GitResult(stdout="", stderr="error", returncode=1)
        assert result.success is False


class TestGitCommand:
    """Tests for git() — low-level command runner."""

    def test_git_returns_result(self, git_repo):
        """git('status') returns a successful GitResult."""
        result = git("status")
        assert isinstance(result, GitResult)
        assert result.success is True

    def test_git_captures_stdout(self, git_repo):
        """git('branch', '--show-current') captures 'main' in stdout."""
        result = git("branch", "--show-current")
        assert result.stdout == "main"

    def test_git_invalid_command_returns_failure(self, git_repo):
        """git with invalid subcommand returns a non-success result."""
        result = git("nonexistent-command")
        assert result.success is False


class TestGitOrThrow:
    """Tests for git_or_throw() — raising command runner."""

    def test_returns_stdout_on_success(self, git_repo):
        """git_or_throw returns stdout for successful command."""
        result = git_or_throw("branch", "--show-current")
        assert result == "main"

    def test_raises_on_failure(self, git_repo):
        """git_or_throw raises RuntimeError on command failure."""
        with pytest.raises(RuntimeError, match="failed"):
            git_or_throw("checkout", "nonexistent-branch-xyz")


class TestBranchOperations:
    """Tests for branch creation, switching, and querying."""

    def test_get_current_branch(self, git_repo):
        """get_current_branch returns 'main' in fresh repo."""
        assert get_current_branch() == "main"

    def test_branch_exists_true(self, git_repo):
        """branch_exists returns True for 'main'."""
        assert branch_exists("main") is True

    def test_branch_exists_false(self, git_repo):
        """branch_exists returns False for nonexistent branch."""
        assert branch_exists("nonexistent") is False

    def test_create_branch_switches(self, git_repo):
        """create_branch creates and checks out the new branch."""
        create_branch("feature-1")
        assert get_current_branch() == "feature-1"

    def test_checkout_existing_branch(self, git_repo):
        """checkout switches to an existing branch."""
        create_branch("feature-1")
        assert get_current_branch() == "feature-1"
        checkout("main")
        assert get_current_branch() == "main"

    def test_list_branches(self, git_repo):
        """list_branches returns all local branches."""
        create_branch("feature-a")
        checkout("main")
        create_branch("feature-b")
        branches = list_branches()
        assert "main" in branches
        assert "feature-a" in branches
        assert "feature-b" in branches


class TestCommitInfo:
    """Tests for commit hash and log queries."""

    def test_get_commit_hash_is_40_chars(self, git_repo):
        """get_commit_hash returns a 40-character hex string."""
        commit_hash = get_commit_hash("HEAD")
        assert len(commit_hash) == 40
        assert all(c in "0123456789abcdef" for c in commit_hash)

    def test_get_short_hash_is_short(self, git_repo):
        """get_short_hash returns a 7-12 character string."""
        short_hash = get_short_hash("HEAD")
        assert 7 <= len(short_hash) <= 12

    def test_get_commit_count(self, git_repo):
        """get_commit_count returns correct count for new commits."""
        create_branch("counting-branch")
        base = get_commit_hash("main")

        (git_repo / "count-file.txt").write_text("content")
        subprocess.run(
            ["git", "add", "."], cwd=str(git_repo), check=True, capture_output=True
        )
        subprocess.run(
            ["git", "commit", "-m", "Add count file"],
            cwd=str(git_repo),
            check=True,
            capture_output=True,
        )

        count = get_commit_count("main", "HEAD")
        assert count == 1

    def test_get_log_oneline(self, git_repo):
        """get_log_oneline returns list containing commit message."""
        create_branch("log-branch")

        (git_repo / "log-file.txt").write_text("log content")
        subprocess.run(
            ["git", "add", "."], cwd=str(git_repo), check=True, capture_output=True
        )
        subprocess.run(
            ["git", "commit", "-m", "Add log file"],
            cwd=str(git_repo),
            check=True,
            capture_output=True,
        )

        log_entries = get_log_oneline("main", "HEAD")
        assert len(log_entries) == 1
        assert "Add log file" in log_entries[0]


class TestWorkingTree:
    """Tests for working tree state detection and stashing."""

    def test_clean_tree(self, git_repo):
        """Fresh repo with no changes is clean."""
        assert is_working_tree_clean() is True

    def test_dirty_tree_untracked(self, git_repo):
        """Untracked file makes working tree dirty."""
        (git_repo / "untracked.txt").write_text("untracked")
        assert is_working_tree_clean() is False

    def test_dirty_tree_modified(self, git_repo):
        """Modified tracked file makes working tree dirty."""
        (git_repo / "README.md").write_text("modified content")
        assert is_working_tree_clean() is False

    def test_stash_push_and_pop(self, git_repo):
        """stash_push saves changes and stash_pop restores them."""
        (git_repo / "README.md").write_text("modified for stash")
        assert is_working_tree_clean() is False

        result = stash_push()
        assert result is True
        assert is_working_tree_clean() is True

        result = stash_pop()
        assert result is True
        assert is_working_tree_clean() is False


class TestRepoDetection:
    """Tests for repository detection utilities."""

    def test_is_git_repo_true(self, git_repo):
        """is_git_repo returns True inside a git repository."""
        assert is_git_repo() is True

    def test_get_git_root(self, git_repo):
        """get_git_root returns the repository root path."""
        root = get_git_root()
        assert root == str(git_repo)

    def test_get_default_branch(self, git_repo):
        """get_default_branch returns 'main' for fixture repo."""
        assert get_default_branch() == "main"
