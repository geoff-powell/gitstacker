"""Integration tests for branch delete command."""

import pytest
from gitstacker.commands.delete import cmd_delete
from gitstacker.commands.create import cmd_create
from gitstacker.commands.stack import cmd_stack
from gitstacker.store import load_state
from gitstacker.git_ops import get_current_branch, checkout, branch_exists


class TestDeleteBranch:
    def test_delete_top_branch(self, stacked_repo):
        checkout("branch-3")
        cmd_delete([])
        state = load_state()
        assert "branch-3" not in state["stacks"]["test-stack"]["branches"]
        assert get_current_branch() != "branch-3"

    def test_delete_middle_reparents_child(self, stacked_repo):
        checkout("branch-2")
        cmd_delete([])
        state = load_state()
        assert state["branches"]["branch-3"]["parent"] == "branch-1"

    def test_delete_bottom_reparents_to_trunk(self, stacked_repo):
        checkout("branch-1")
        cmd_delete([])
        state = load_state()
        assert state["branches"]["branch-2"]["parent"] == "main"

    def test_delete_by_name(self, stacked_repo):
        checkout("main")
        cmd_delete(["branch-2"])
        state = load_state()
        assert "branch-2" not in state["stacks"]["test-stack"]["branches"]

    def test_delete_non_stacked_errors(self, stacked_repo):
        with pytest.raises(SystemExit):
            cmd_delete(["nonexistent"])

    def test_delete_with_force_removes_git_branch(self, stacked_repo):
        checkout("main")
        cmd_delete(["branch-3", "--force"])
        assert not branch_exists("branch-3")

    def test_delete_no_move_message_when_not_on_branch(self, stacked_repo, capsys):
        """Bug #9: Don't print 'Moved to' when not on the deleted branch."""
        checkout("main")
        cmd_delete(["branch-3"])
        captured = capsys.readouterr()
        assert "moved to" not in captured.out.lower()
