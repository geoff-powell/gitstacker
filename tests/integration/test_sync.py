"""Integration tests for gs sync command."""

import pytest
import subprocess
import os
import tempfile
from gitstacker.commands.sync import cmd_sync
from gitstacker.commands.init import cmd_init
from gitstacker.commands.create import cmd_create
from gitstacker.commands.stack import cmd_stack
from gitstacker.git_ops import get_current_branch, checkout, get_commit_hash
from gitstacker.store import load_state


def get_remote_path(repo):
    """Get the remote origin URL from a repo."""
    result = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        cwd=str(repo), capture_output=True, text=True
    )
    return result.stdout.strip()


def advance_remote(repo):
    """Simulate someone pushing to trunk on remote by cloning, committing, pushing."""
    remote_url = get_remote_path(repo)
    with tempfile.TemporaryDirectory() as td:
        other = os.path.join(td, "other")
        subprocess.run(["git", "clone", remote_url, other], check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "other@test.com"], cwd=other, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Other"], cwd=other, check=True, capture_output=True)
        filepath = os.path.join(other, "remote-change.txt")
        with open(filepath, "w") as f:
            f.write("remote change")
        subprocess.run(["git", "add", "."], cwd=other, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Remote commit"], cwd=other, check=True, capture_output=True)
        subprocess.run(["git", "push"], cwd=other, check=True, capture_output=True)


class TestSync:
    def test_sync_from_trunk(self, repo_with_remote):
        """Bug #7: sync works when already on trunk."""
        cmd_init([])
        cmd_stack(["new", "s"])
        cmd_create(["b1"])
        checkout("main")

        advance_remote(repo_with_remote)
        cmd_sync([])

        assert get_current_branch() == "main"

    def test_sync_from_branch(self, repo_with_remote):
        """Sync from a stacked branch returns to that branch."""
        cmd_init([])
        cmd_stack(["new", "s"])
        cmd_create(["b1"])
        (repo_with_remote / "b1.txt").write_text("content")
        subprocess.run(["git", "add", "."], cwd=str(repo_with_remote), check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "B1 work"], cwd=str(repo_with_remote), check=True, capture_output=True)

        advance_remote(repo_with_remote)
        cmd_sync([])

        assert get_current_branch() == "b1"

    def test_sync_updates_trunk(self, repo_with_remote):
        """Sync pulls new commits into trunk."""
        cmd_init([])
        cmd_stack(["new", "s"])
        cmd_create(["b1"])

        advance_remote(repo_with_remote)
        trunk_before = get_commit_hash("main")
        cmd_sync([])

        checkout("main")
        trunk_after = get_commit_hash("HEAD")
        assert trunk_before != trunk_after

    def test_sync_restacks_after_pull(self, repo_with_remote):
        """Sync restacks branches after pulling trunk."""
        cmd_init([])
        cmd_stack(["new", "s"])
        cmd_create(["b1"])
        (repo_with_remote / "b1.txt").write_text("content")
        subprocess.run(["git", "add", "."], cwd=str(repo_with_remote), check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "B1 work"], cwd=str(repo_with_remote), check=True, capture_output=True)

        advance_remote(repo_with_remote)
        cmd_sync([])

        # b1 should now be based on the updated trunk
        checkout("b1")
        state = load_state()
        assert state["branches"]["b1"]["commit_base"] is not None
