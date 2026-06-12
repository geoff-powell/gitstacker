# Task 12: Fix Sync Bug (Already on Trunk) + Integration Test

## Description
Fix Bug #7: `gs sync` fails when the user is already on trunk because it tries to `checkout(trunk)` (no-op that succeeds) but then `checkout(current_branch)` at the end checks out trunk again unnecessarily. The real issue is that if `current_branch == trunk`, the "return to original branch" logic is redundant. Also write integration tests for the sync command using a bare remote repo.

## Files to Create/Modify
- `gitstacker/commands/sync.py` — Fix redundant checkout when already on trunk
- `tests/integration/test_sync.py` — Integration tests for sync command
- `tests/conftest.py` — Add `remote_repo` fixture (bare repo as remote)

## Implementation Details

### Fix sync.py (Bug #7)

```python
def cmd_sync(args: list[str]) -> None:
    state = load_state()
    current_branch = get_current_branch()

    info("Fetching from remote...")
    fetch_remote()

    # Update trunk
    trunk = state["trunk"]
    info(f"Updating trunk ({trunk})...")

    # Only checkout trunk if we're not already on it
    if current_branch != trunk:
        checkout(trunk)

    result = pull_rebase(trunk)

    if not result.success:
        error(f"Failed to update trunk: {result.stderr}")
        if current_branch != trunk:
            checkout(current_branch)
        raise SystemExit(1)

    success(f"Trunk updated: {trunk}")

    # Return to original branch (only if we moved)
    if current_branch != trunk:
        checkout(current_branch)

    # Restack
    print()
    cmd_restack(args)
```

### Add remote_repo fixture to conftest.py

```python
@pytest.fixture
def remote_repo(tmp_path):
    """Create a bare remote repo and a local clone for sync testing."""
    bare = tmp_path / "remote.git"
    bare.mkdir()
    subprocess.run(["git", "init", "--bare", "-b", "main"], cwd=bare, check=True)

    local = tmp_path / "local"
    subprocess.run(["git", "clone", str(bare), str(local)], check=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=local, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=local, check=True)

    # Initial commit
    (local / "README.md").write_text("# Test")
    subprocess.run(["git", "add", "."], cwd=local, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=local, check=True)
    subprocess.run(["git", "push", "-u", "origin", "main"], cwd=local, check=True)

    return {"bare": bare, "local": local}
```

### test_sync.py

```python
import pytest
import subprocess
import os
from gitstacker.commands.sync import cmd_sync
from gitstacker.commands.init import cmd_init
from gitstacker.commands.create import cmd_create
from gitstacker.commands.stack import cmd_stack
from gitstacker.git_ops import get_current_branch, checkout, get_commit_hash
from gitstacker.store import load_state


def advance_remote(bare_path, local_path):
    """Simulate someone pushing to trunk on remote."""
    # Clone remote to a temp location, commit, push
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        other = os.path.join(td, "other")
        subprocess.run(["git", "clone", str(bare_path), other], check=True)
        subprocess.run(["git", "config", "user.email", "other@test.com"], cwd=other, check=True)
        subprocess.run(["git", "config", "user.name", "Other"], cwd=other, check=True)
        filepath = os.path.join(other, "remote-change.txt")
        with open(filepath, "w") as f:
            f.write("remote change")
        subprocess.run(["git", "add", "."], cwd=other, check=True)
        subprocess.run(["git", "commit", "-m", "Remote commit"], cwd=other, check=True)
        subprocess.run(["git", "push"], cwd=other, check=True)


class TestSync:
    def test_sync_from_trunk(self, remote_repo, monkeypatch):
        """Bug #7: sync works when already on trunk."""
        local = remote_repo["local"]
        monkeypatch.chdir(local)
        cmd_init([])
        cmd_stack(["new", "s"])
        cmd_create(["b1"])
        checkout("main")

        advance_remote(remote_repo["bare"], local)
        cmd_sync([])

        assert get_current_branch() == "main"

    def test_sync_from_branch(self, remote_repo, monkeypatch):
        """Sync from a stacked branch returns to that branch."""
        local = remote_repo["local"]
        monkeypatch.chdir(local)
        cmd_init([])
        cmd_stack(["new", "s"])
        cmd_create(["b1"])
        (local / "b1.txt").write_text("content")
        subprocess.run(["git", "add", "."], cwd=local, check=True)
        subprocess.run(["git", "commit", "-m", "B1 work"], cwd=local, check=True)

        advance_remote(remote_repo["bare"], local)
        cmd_sync([])

        assert get_current_branch() == "b1"

    def test_sync_updates_trunk(self, remote_repo, monkeypatch):
        """Sync pulls new commits into trunk."""
        local = remote_repo["local"]
        monkeypatch.chdir(local)
        cmd_init([])
        cmd_stack(["new", "s"])
        cmd_create(["b1"])

        advance_remote(remote_repo["bare"], local)
        trunk_before = get_commit_hash("main")
        cmd_sync([])

        checkout("main")
        trunk_after = get_commit_hash("HEAD")
        assert trunk_before != trunk_after

    def test_sync_restacks_after_pull(self, remote_repo, monkeypatch):
        """Sync restacks branches after pulling trunk."""
        local = remote_repo["local"]
        monkeypatch.chdir(local)
        cmd_init([])
        cmd_stack(["new", "s"])
        cmd_create(["b1"])
        (local / "b1.txt").write_text("content")
        subprocess.run(["git", "add", "."], cwd=local, check=True)
        subprocess.run(["git", "commit", "-m", "B1 work"], cwd=local, check=True)

        advance_remote(remote_repo["bare"], local)
        cmd_sync([])

        # b1 should now be based on the updated trunk
        checkout("b1")
        state = load_state()
        assert state["branches"]["b1"]["commit_base"] is not None
```

## Dependencies
- Depends on: task-02 (test infrastructure), task-08 (restack fixes — sync calls restack)

## Acceptance Criteria
- [ ] `gs sync` works when already on trunk (no crash, Bug #7 fixed)
- [ ] `gs sync` returns to original branch after sync
- [ ] `gs sync` pulls new remote commits into trunk
- [ ] `gs sync` restacks branches after pulling
- [ ] `remote_repo` fixture provides a working bare remote + local clone
- [ ] `pytest tests/integration/test_sync.py -v` passes all tests
- [ ] At least 4 test cases

## Notes
- The `remote_repo` fixture needs to create a bare repo and clone it (not just `git init`), since `git pull` requires a remote.
- Use a helper function to "advance" the remote by cloning it elsewhere, committing, and pushing.
- Sync tests are slower due to network-like operations (clone, push, pull) — but they're all local.
- The `fetch_remote()` call in sync.py may fail if there's no remote configured — the fixture handles this.
