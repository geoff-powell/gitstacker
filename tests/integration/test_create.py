"""Integration tests for gs create command."""

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
        subprocess.run(["git", "add", "."], cwd=str(initialized_repo), check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "commit on a"], cwd=str(initialized_repo), check=True, capture_output=True)
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
