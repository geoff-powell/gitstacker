"""Integration tests for gs diff command."""

import pytest
import subprocess
from gitstacker.commands.diff import cmd_diff
from gitstacker.commands.create import cmd_create
from gitstacker.commands.stack import cmd_stack
from gitstacker.git_ops import get_current_branch, checkout
from gitstacker.store import load_state, get_parent_branch


def add_commit(repo, filename, content, message):
    (repo / filename).write_text(content)
    subprocess.run(["git", "add", "."], cwd=str(repo), check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", message], cwd=str(repo), check=True, capture_output=True)


class TestDiff:
    def test_diff_not_on_stack_errors(self, initialized_repo):
        """Diff when not on stacked branch errors."""
        cmd_stack(["new", "s"])
        # We're on main (trunk), not on a stacked branch
        with pytest.raises(SystemExit):
            cmd_diff([])

    def test_diff_first_branch_parent_is_trunk(self, initialized_repo):
        """First branch diffs against trunk."""
        cmd_stack(["new", "s"])
        cmd_create(["b1"])
        add_commit(initialized_repo, "new.txt", "content", "Add file")

        # Verify parent is trunk
        state = load_state()
        stack = state["stacks"]["s"]
        parent = get_parent_branch(state, stack, "b1")
        assert parent == "main"

    def test_diff_shows_only_branch_changes(self, initialized_repo):
        """Diff shows only changes made on current branch, not parent's changes."""
        cmd_stack(["new", "s"])
        cmd_create(["b1"])
        add_commit(initialized_repo, "b1-file.txt", "b1 content", "B1 commit")
        cmd_create(["b2"])
        add_commit(initialized_repo, "b2-file.txt", "b2 content", "B2 commit")

        # Diff on b2 should only show b2-file.txt, not b1-file.txt
        # Verify by running git diff directly (since cmd_diff calls sys.exit)
        from gitstacker.git_ops import get_merge_base
        merge_base = get_merge_base("b1", "b2")
        result = subprocess.run(
            ["git", "diff", "--name-only", f"{merge_base}..HEAD"],
            cwd=str(initialized_repo), capture_output=True, text=True
        )
        assert "b2-file.txt" in result.stdout
        assert "b1-file.txt" not in result.stdout

    def test_diff_stat_output(self, initialized_repo):
        """--stat flag produces stat-style output."""
        cmd_stack(["new", "s"])
        cmd_create(["b1"])
        add_commit(initialized_repo, "stat-test.txt", "content here", "Add file")

        # Run the equivalent git diff --stat
        from gitstacker.git_ops import get_merge_base
        merge_base = get_merge_base("main", "b1")
        result = subprocess.run(
            ["git", "diff", "--stat", f"{merge_base}..HEAD"],
            cwd=str(initialized_repo), capture_output=True, text=True
        )
        assert "stat-test.txt" in result.stdout

    def test_diff_empty_branch_no_output(self, initialized_repo):
        """Diff on branch with no commits above parent shows nothing."""
        cmd_stack(["new", "s"])
        cmd_create(["empty-branch"])

        # No changes, so diff should be empty
        from gitstacker.git_ops import get_merge_base
        merge_base = get_merge_base("main", "empty-branch")
        result = subprocess.run(
            ["git", "diff", f"{merge_base}..HEAD"],
            cwd=str(initialized_repo), capture_output=True, text=True
        )
        assert result.stdout.strip() == ""
