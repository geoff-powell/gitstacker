"""Integration tests for trunk command."""

import pytest
import subprocess
from gitstacker.commands.trunk import cmd_trunk
from gitstacker.store import load_state


class TestTrunk:
    def test_show_trunk(self, initialized_repo, capsys):
        cmd_trunk([])
        captured = capsys.readouterr()
        assert "main" in captured.out

    def test_set_trunk(self, initialized_repo):
        subprocess.run(["git", "branch", "develop"], cwd=str(initialized_repo), check=True, capture_output=True)
        cmd_trunk(["develop"])
        state = load_state()
        assert state["trunk"] == "develop"

    def test_set_nonexistent_errors(self, initialized_repo):
        with pytest.raises(SystemExit):
            cmd_trunk(["nonexistent"])

    def test_set_trunk_updates_stacks(self, stacked_repo):
        """Bug #11: Setting trunk updates stacks referencing old trunk."""
        subprocess.run(["git", "branch", "develop"], cwd=str(stacked_repo), check=True, capture_output=True)
        cmd_trunk(["develop"])
        state = load_state()
        assert state["stacks"]["test-stack"]["trunk"] == "develop"
