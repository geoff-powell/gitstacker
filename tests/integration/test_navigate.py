"""Integration tests for gs up/down/top/bottom navigation commands."""

import pytest
from gitstacker.commands.navigate import cmd_navigate
from gitstacker.git_ops import get_current_branch, checkout, create_branch


class TestNavigateUp:
    def test_up_from_bottom(self, stacked_repo):
        """Up from branch-1 goes to branch-2."""
        checkout("branch-1")
        cmd_navigate("up", [])
        assert get_current_branch() == "branch-2"

    def test_up_from_middle(self, stacked_repo):
        """Up from branch-2 goes to branch-3."""
        checkout("branch-2")
        cmd_navigate("up", [])
        assert get_current_branch() == "branch-3"

    def test_up_from_top_warns(self, stacked_repo, capsys):
        """Up from branch-3 (top) shows warning, stays put."""
        checkout("branch-3")
        cmd_navigate("up", [])
        assert get_current_branch() == "branch-3"
        captured = capsys.readouterr()
        assert "top" in captured.out.lower()

    def test_up_by_2(self, stacked_repo):
        """Up 2 from branch-1 goes to branch-3."""
        checkout("branch-1")
        cmd_navigate("up", ["2"])
        assert get_current_branch() == "branch-3"

    def test_up_clamped_at_top(self, stacked_repo):
        """Up 100 from branch-1 goes to branch-3 (clamped)."""
        checkout("branch-1")
        cmd_navigate("up", ["100"])
        assert get_current_branch() == "branch-3"


class TestNavigateDown:
    def test_down_from_top(self, stacked_repo):
        """Down from branch-3 goes to branch-2."""
        checkout("branch-3")
        cmd_navigate("down", [])
        assert get_current_branch() == "branch-2"

    def test_down_from_bottom_warns(self, stacked_repo, capsys):
        """Down from branch-1 (bottom) shows warning, stays put."""
        checkout("branch-1")
        cmd_navigate("down", [])
        assert get_current_branch() == "branch-1"
        captured = capsys.readouterr()
        assert "bottom" in captured.out.lower()

    def test_down_by_2(self, stacked_repo):
        """Down 2 from branch-3 goes to branch-1."""
        checkout("branch-3")
        cmd_navigate("down", ["2"])
        assert get_current_branch() == "branch-1"


class TestNavigateTopBottom:
    def test_top_from_bottom(self, stacked_repo):
        """Top from branch-1 goes to branch-3."""
        checkout("branch-1")
        cmd_navigate("top", [])
        assert get_current_branch() == "branch-3"

    def test_bottom_from_top(self, stacked_repo):
        """Bottom from branch-3 goes to branch-1."""
        checkout("branch-3")
        cmd_navigate("bottom", [])
        assert get_current_branch() == "branch-1"

    def test_top_when_already_at_top(self, stacked_repo, capsys):
        """Top when at top shows warning."""
        checkout("branch-3")
        cmd_navigate("top", [])
        assert get_current_branch() == "branch-3"
        captured = capsys.readouterr()
        assert "top" in captured.out.lower()


class TestNavigateFromTrunk:
    """Tests for Bug #4 fix: navigation from trunk."""

    def test_up_from_trunk_goes_to_bottom(self, stacked_repo):
        """Up from trunk goes to branches[0] (bottom)."""
        checkout("main")
        cmd_navigate("up", [])
        assert get_current_branch() == "branch-1"

    def test_top_from_trunk_goes_to_top(self, stacked_repo):
        """Top from trunk goes to branches[-1]."""
        checkout("main")
        cmd_navigate("top", [])
        assert get_current_branch() == "branch-3"

    def test_bottom_from_trunk_goes_to_bottom(self, stacked_repo):
        """Bottom from trunk goes to branches[0]."""
        checkout("main")
        cmd_navigate("bottom", [])
        assert get_current_branch() == "branch-1"

    def test_down_from_trunk_warns(self, stacked_repo, capsys):
        """Down from trunk shows warning (can't go below trunk)."""
        checkout("main")
        cmd_navigate("down", [])
        # Should warn, not crash, and stay on main
        assert get_current_branch() == "main"


class TestNavigateErrorCases:
    """Tests for Bug #8 fix and other error cases."""

    def test_non_numeric_arg_errors(self, stacked_repo):
        """gs up abc shows error, exits 1."""
        checkout("branch-1")
        with pytest.raises(SystemExit):
            cmd_navigate("up", ["abc"])

    def test_zero_arg_errors(self, stacked_repo):
        """gs up 0 shows error, exits 1."""
        checkout("branch-1")
        with pytest.raises(SystemExit):
            cmd_navigate("up", ["0"])

    def test_negative_arg_errors(self, stacked_repo):
        """gs up -1 shows error, exits 1."""
        checkout("branch-1")
        with pytest.raises(SystemExit):
            cmd_navigate("up", ["-1"])

    def test_not_on_stack_errors(self, stacked_repo):
        """Navigate when not on any stacked branch errors."""
        create_branch("unrelated")
        with pytest.raises(SystemExit):
            cmd_navigate("up", [])

    def test_dirty_tree_errors(self, stacked_repo):
        """Navigate with dirty working tree errors."""
        checkout("branch-1")
        (stacked_repo / "dirty.txt").write_text("dirty")
        with pytest.raises(SystemExit):
            cmd_navigate("up", [])
