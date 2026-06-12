"""
Shared test fixtures for GitStacker tests.
Creates real git repositories in temp directories for integration testing.
"""

import os
import subprocess
import pytest


@pytest.fixture
def git_repo(tmp_path, monkeypatch):
    """Create a bare git repo with an initial commit on 'main'."""
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.chdir(repo)
    subprocess.run(["git", "init", "-b", "main"], cwd=str(repo), check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=str(repo), check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=str(repo), check=True, capture_output=True)
    # Initial commit
    (repo / "README.md").write_text("# Test")
    subprocess.run(["git", "add", "."], cwd=str(repo), check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=str(repo), check=True, capture_output=True)
    return repo


@pytest.fixture
def initialized_repo(git_repo):
    """A git repo with gitstacker initialized."""
    from gitstacker.store import init_state
    init_state("main")
    return git_repo


@pytest.fixture
def stacked_repo(initialized_repo):
    """A repo with gitstacker initialized and a stack with 3 branches."""
    from gitstacker.store import load_state, save_state, create_stack, add_branch_to_stack
    from gitstacker.git_ops import create_branch, get_commit_hash
    import subprocess

    state = load_state()
    create_stack(state, "test-stack", "main")
    state["current_stack"] = "test-stack"

    # Create 3 branches with commits
    for i, name in enumerate(["branch-1", "branch-2", "branch-3"]):
        parent = "main" if i == 0 else f"branch-{i}"
        create_branch(name)
        # Add a commit
        (initialized_repo / f"file-{name}.txt").write_text(f"content for {name}")
        subprocess.run(["git", "add", "."], cwd=str(initialized_repo), check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", f"Add {name}"], cwd=str(initialized_repo), check=True, capture_output=True)
        add_branch_to_stack(state, "test-stack", name, parent)
        state["branches"][name]["commit_base"] = get_commit_hash("HEAD")

    save_state(state)
    return initialized_repo


@pytest.fixture
def repo_with_remote(tmp_path, monkeypatch):
    """A git repo with a bare remote for testing push/sync operations."""
    # Create bare remote
    remote_path = tmp_path / "remote.git"
    remote_path.mkdir()
    subprocess.run(["git", "init", "--bare", "-b", "main"], cwd=str(remote_path), check=True, capture_output=True)

    # Create working repo
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.chdir(repo)
    subprocess.run(["git", "init", "-b", "main"], cwd=str(repo), check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=str(repo), check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=str(repo), check=True, capture_output=True)
    subprocess.run(["git", "remote", "add", "origin", str(remote_path)], cwd=str(repo), check=True, capture_output=True)

    # Initial commit and push
    (repo / "README.md").write_text("# Test")
    subprocess.run(["git", "add", "."], cwd=str(repo), check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=str(repo), check=True, capture_output=True)
    subprocess.run(["git", "push", "-u", "origin", "main"], cwd=str(repo), check=True, capture_output=True)

    return repo


def run_gs(*args):
    """Run a gs CLI command via subprocess and return (returncode, stdout, stderr).
    
    Uses subprocess for true process isolation in tests.
    """
    result = subprocess.run(
        ["gs", *args],
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout, result.stderr
