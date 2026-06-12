"""Integration tests for stack management commands."""

import pytest
from gitstacker.commands.stack import cmd_stack
from gitstacker.commands.create import cmd_create
from gitstacker.store import load_state
from gitstacker.git_ops import get_current_branch, checkout


class TestStackNew:
    def test_create_stack(self, initialized_repo):
        cmd_stack(["new", "my-stack"])
        state = load_state()
        assert "my-stack" in state["stacks"]
        assert state["current_stack"] == "my-stack"

    def test_create_duplicate_errors(self, initialized_repo):
        cmd_stack(["new", "s"])
        with pytest.raises(SystemExit):
            cmd_stack(["new", "s"])

    def test_create_no_name_errors(self, initialized_repo):
        with pytest.raises(SystemExit):
            cmd_stack(["new"])


class TestStackList:
    def test_list_empty(self, initialized_repo, capsys):
        cmd_stack(["list"])
        captured = capsys.readouterr()
        assert "no stacks" in captured.out.lower()

    def test_list_shows_stacks(self, initialized_repo, capsys):
        cmd_stack(["new", "stack-a"])
        cmd_stack(["new", "stack-b"])
        cmd_stack(["list"])
        captured = capsys.readouterr()
        assert "stack-a" in captured.out
        assert "stack-b" in captured.out

    def test_list_shows_active(self, stacked_repo, capsys):
        checkout("branch-1")
        cmd_stack(["list"])
        captured = capsys.readouterr()
        assert "active" in captured.out.lower()


class TestStackSwitch:
    def test_switch_to_existing(self, initialized_repo):
        cmd_stack(["new", "stack-a"])
        cmd_create(["br-a"])
        checkout("main")
        cmd_stack(["new", "stack-b"])
        cmd_create(["br-b"])
        cmd_stack(["switch", "stack-a"])
        state = load_state()
        assert state["current_stack"] == "stack-a"
        assert get_current_branch() == "br-a"

    def test_switch_nonexistent_errors(self, initialized_repo):
        with pytest.raises(SystemExit):
            cmd_stack(["switch", "nope"])

    def test_switch_no_name_errors(self, initialized_repo):
        with pytest.raises(SystemExit):
            cmd_stack(["switch"])


class TestStackDelete:
    def test_delete_stack(self, initialized_repo):
        cmd_stack(["new", "to-delete"])
        cmd_stack(["delete", "to-delete"])
        state = load_state()
        assert "to-delete" not in state["stacks"]

    def test_delete_clears_current_stack(self, initialized_repo):
        cmd_stack(["new", "only-stack"])
        cmd_stack(["delete", "only-stack"])
        state = load_state()
        assert state["current_stack"] is None

    def test_delete_nonexistent_errors(self, initialized_repo):
        with pytest.raises(SystemExit):
            cmd_stack(["delete", "ghost"])
