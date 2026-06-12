"""Integration tests for gs init command."""

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
