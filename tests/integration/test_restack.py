"""Integration tests for gs restack command."""

import pytest
import subprocess
from gitstacker.commands.restack import cmd_restack
from gitstacker.commands.create import cmd_create
from gitstacker.commands.stack import cmd_stack
from gitstacker.git_ops import (
    get_current_branch, checkout, get_commit_hash, get_commit_count,
    is_working_tree_clean,
)
from gitstacker.store import load_state, save_state


def add_commit(repo, filename, content, message):
    """Helper: add a file and commit."""
    (repo / filename).write_text(content)
    subprocess.run(["git", "add", "."], cwd=str(repo), check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", message], cwd=str(repo), check=True, capture_output=True)


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
        result = subprocess.run(
            ["git", "merge-base", "main", "branch-1"],
            cwd=str(stacked_repo), capture_output=True, text=True
        )
        merge_base = result.stdout.strip()
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
        """All 3 branches are rebased and commit_bases updated."""
        checkout("main")
        add_commit(stacked_repo, "new.txt", "x", "Trunk update")
        checkout("branch-1")
        cmd_restack([])
        state = load_state()
        # All commit_bases should be updated
        for branch in ["branch-1", "branch-2", "branch-3"]:
            assert state["branches"][branch]["commit_base"] is not None

    def test_restack_returns_to_original_branch(self, stacked_repo):
        """After restack, user is back on their original branch."""
        checkout("main")
        add_commit(stacked_repo, "new.txt", "x", "Trunk update")
        checkout("branch-2")
        cmd_restack([])
        assert get_current_branch() == "branch-2"

    def test_restack_clears_progress_on_success(self, stacked_repo):
        """Successful restack clears _restack_progress from state."""
        checkout("main")
        add_commit(stacked_repo, "new.txt", "x", "Trunk update")
        checkout("branch-1")
        cmd_restack([])
        state = load_state()
        assert "_restack_progress" not in state


class TestRestackConflicts:
    def test_restack_conflict_saves_progress(self, initialized_repo):
        """Conflicting rebase saves _restack_progress to state."""
        cmd_stack(["new", "s"])

        # Create branch-1 with a file
        cmd_create(["branch-1"])
        add_commit(initialized_repo, "conflict.txt", "from branch-1", "B1 commit")

        # Create branch-2
        cmd_create(["branch-2"])
        add_commit(initialized_repo, "other.txt", "branch-2 stuff", "B2 commit")

        # Modify SAME file on trunk to cause conflict with branch-1
        checkout("main")
        add_commit(initialized_repo, "conflict.txt", "from trunk DIFFERENT", "Trunk conflict")

        # Restack should fail on branch-1
        checkout("branch-1")
        cmd_restack([])

        state = load_state()
        assert "_restack_progress" in state
        assert state["_restack_progress"]["failed_at"] == "branch-1"

    def test_restack_conflict_working_tree_clean(self, initialized_repo):
        """After conflict abort, working tree is clean."""
        cmd_stack(["new", "s"])
        cmd_create(["b1"])
        add_commit(initialized_repo, "f.txt", "content", "commit")

        checkout("main")
        add_commit(initialized_repo, "f.txt", "conflict!", "trunk change")

        checkout("b1")
        cmd_restack([])

        # Working tree should be clean after abort
        assert is_working_tree_clean()


class TestRestackStash:
    def test_restack_stashes_dirty_tree(self, stacked_repo, capsys):
        """Dirty working tree is stashed before restack."""
        checkout("branch-1")
        (stacked_repo / "dirty.txt").write_text("uncommitted")
        subprocess.run(["git", "add", "dirty.txt"], cwd=str(stacked_repo), check=True, capture_output=True)
        cmd_restack([])
        captured = capsys.readouterr()
        assert "stash" in captured.out.lower()

    def test_restack_restores_stash_on_success(self, stacked_repo):
        """Stashed changes are restored after successful restack."""
        checkout("branch-1")
        # Stage a new file that won't conflict with rebase
        (stacked_repo / "local-notes.txt").write_text("my local notes")
        subprocess.run(["git", "add", "local-notes.txt"], cwd=str(stacked_repo), check=True, capture_output=True)
        cmd_restack([])
        # File should still exist (restored from stash)
        assert (stacked_repo / "local-notes.txt").exists()


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
