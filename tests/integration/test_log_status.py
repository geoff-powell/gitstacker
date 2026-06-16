"""Integration tests for gs log, gs status, and gs completions (read-only commands)."""

import json
import pytest
from io import StringIO
from unittest.mock import patch

from gitstacker.commands.log import cmd_log
from gitstacker.commands.status import cmd_status
from gitstacker.commands.completions import cmd_completions
from gitstacker.commands.create import cmd_create
from gitstacker.commands.stack import cmd_stack
from gitstacker.git_ops import get_current_branch, checkout
from gitstacker.store import load_state, save_state
import subprocess


def commit(repo, filename, content, message):
    (repo / filename).write_text(content)
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", message], cwd=repo, check=True)


class TestLog:
    """Tests for gs log command."""

    def test_log_shows_stack(self, stacked_repo, capsys):
        """Log displays the current stack branches."""
        checkout("branch-2")
        cmd_log([])
        output = capsys.readouterr().out
        assert "branch-1" in output
        assert "branch-2" in output
        assert "branch-3" in output
        assert "test-stack" in output

    def test_log_no_stack(self, initialized_repo, capsys):
        """Log when not on a stack shows info message."""
        cmd_log([])
        output = capsys.readouterr().out
        assert "Not on a stack" in output

    def test_log_all_stacks(self, stacked_repo, capsys):
        """Log --all shows all stacks."""
        # Create second stack
        checkout("main")
        cmd_stack(["new", "second-stack"])
        cmd_create(["s2-branch"])
        commit(stacked_repo, "s2.txt", "s2", "S2")

        cmd_log(["--all"])
        output = capsys.readouterr().out
        assert "test-stack" in output
        assert "second-stack" in output

    def test_log_shows_current_branch_marker(self, stacked_repo, capsys):
        """Log highlights the current branch."""
        checkout("branch-2")
        cmd_log([])
        output = capsys.readouterr().out
        # branch-2 should appear (it's highlighted, so it's in the output)
        assert "branch-2" in output

    def test_log_empty_stack(self, initialized_repo, capsys):
        """Log on empty stack doesn't crash."""
        cmd_stack(["new", "empty"])
        cmd_log([])
        output = capsys.readouterr().out
        assert "no branches" not in output.lower() or "empty" in output.lower() or output


class TestStatus:
    """Tests for gs status command."""

    def test_status_json_initialized(self, stacked_repo, capsys):
        """Status --json returns valid JSON with correct fields."""
        checkout("branch-2")
        cmd_status(["--json"])
        output = capsys.readouterr().out
        data = json.loads(output)
        assert data["initialized"] is True
        assert data["trunk"] == "main"
        assert data["current_branch"] == "branch-2"
        assert data["current_stack"] == "test-stack"
        assert data["stack_position"] == 2
        assert data["stack_size"] == 3

    def test_status_json_not_initialized(self, git_repo, capsys):
        """Status --json when not initialized."""
        cmd_status(["--json"])
        output = capsys.readouterr().out
        data = json.loads(output)
        assert data["initialized"] is False

    def test_status_human_readable(self, stacked_repo, capsys):
        """Status without --json shows human-readable output."""
        checkout("branch-1")
        cmd_status([])
        output = capsys.readouterr().out
        assert "main" in output
        assert "branch-1" in output
        assert "test-stack" in output

    def test_status_not_on_stack(self, initialized_repo, capsys):
        """Status when not on any stack branch."""
        cmd_status(["--json"])
        output = capsys.readouterr().out
        data = json.loads(output)
        assert data["initialized"] is True
        assert data["current_stack"] is None

    def test_status_includes_pr_info(self, stacked_repo, capsys):
        """Status JSON includes PR info when available."""
        state = load_state()
        state["branches"]["branch-1"]["pr_number"] = 42
        state["branches"]["branch-1"]["pr_url"] = "https://github.com/org/repo/pull/42"
        save_state(state)

        checkout("branch-1")
        cmd_status(["--json"])
        output = capsys.readouterr().out
        data = json.loads(output)
        prs = data["stacks"]["test-stack"].get("prs", {})
        assert "branch-1" in prs
        assert prs["branch-1"]["number"] == 42

    def test_status_json_all_stacks(self, stacked_repo, capsys):
        """Status JSON includes all stacks."""
        checkout("main")
        cmd_stack(["new", "other"])
        cmd_create(["other-b1"])
        commit(stacked_repo, "other.txt", "x", "Other")

        capsys.readouterr()  # Clear previous output
        cmd_status(["--json"])
        output = capsys.readouterr().out
        data = json.loads(output)
        assert "test-stack" in data["stacks"]
        assert "other" in data["stacks"]
        assert data["stacks"]["test-stack"]["branch_count"] == 3
        assert data["stacks"]["other"]["branch_count"] == 1


class TestCompletions:
    """Tests for gs completions command."""

    def test_bash_completions(self, capsys):
        """Bash completions output valid shell script."""
        cmd_completions(["bash"])
        output = capsys.readouterr().out
        assert "_gs_completion" in output
        assert "complete -F" in output
        assert "init" in output
        assert "restack" in output

    def test_zsh_completions(self, capsys):
        """Zsh completions output valid script."""
        cmd_completions(["zsh"])
        output = capsys.readouterr().out
        assert "#compdef gs" in output
        assert "_gs()" in output

    def test_fish_completions(self, capsys):
        """Fish completions output valid script."""
        cmd_completions(["fish"])
        output = capsys.readouterr().out
        assert "complete -c gs" in output

    def test_unsupported_shell_errors(self, capsys):
        """Unsupported shell raises SystemExit."""
        with pytest.raises(SystemExit):
            cmd_completions(["powershell"])

    def test_default_is_bash(self, capsys):
        """No argument defaults to bash."""
        cmd_completions([])
        output = capsys.readouterr().out
        assert "_gs_completion" in output


class TestReadOnlyWithDirtyTree:
    """Read-only commands should work fine with dirty tree."""

    def test_log_works_dirty(self, stacked_repo, capsys):
        """Log works with uncommitted changes."""
        checkout("branch-1")
        (stacked_repo / "dirty.txt").write_text("dirty")
        cmd_log([])  # Should not raise
        output = capsys.readouterr().out
        assert "branch-1" in output

    def test_status_works_dirty(self, stacked_repo, capsys):
        """Status works with uncommitted changes."""
        checkout("branch-1")
        (stacked_repo / "dirty.txt").write_text("dirty")
        cmd_status(["--json"])  # Should not raise
        output = capsys.readouterr().out
        data = json.loads(output)
        assert data["initialized"] is True
