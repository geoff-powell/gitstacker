# Task 02: Set Up Test Infrastructure

## Description
Set up pytest configuration, install test dependencies, and create `tests/conftest.py` with shared fixtures that create real git repositories for integration testing. This provides the foundation for all subsequent test tasks.

## Files to Create/Modify
- `pyproject.toml` — Add pytest, pytest-cov as dev dependencies; add `[tool.pytest.ini_options]` config
- `tests/__init__.py` — Empty package marker
- `tests/conftest.py` — Shared fixtures: `git_repo`, `initialized_repo`, `stacked_repo`
- `tests/unit/__init__.py` — Empty package marker
- `tests/integration/__init__.py` — Empty package marker
- `tests/e2e/__init__.py` — Empty package marker

## Implementation Details

### pyproject.toml additions

```toml
[project.optional-dependencies]
dev = ["pytest>=7.0", "pytest-cov>=4.0"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-v --tb=short"
markers = [
    "unit: Unit tests (no git repos)",
    "integration: Integration tests (real git repos)",
    "e2e: End-to-end workflow tests",
]
```

### Shared Fixtures in `tests/conftest.py`

```python
import os
import subprocess
import pytest

@pytest.fixture
def git_repo(tmp_path, monkeypatch):
    """Create a bare git repo with an initial commit on 'main'."""
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.chdir(repo)
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    # Initial commit
    (repo / "README.md").write_text("# Test")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo, check=True)
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
    from gitstacker.git_ops import create_branch, checkout, get_commit_hash
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
        subprocess.run(["git", "add", "."], cwd=initialized_repo, check=True)
        subprocess.run(["git", "commit", "-m", f"Add {name}"], cwd=initialized_repo, check=True)
        add_branch_to_stack(state, "test-stack", name, parent)
        state["branches"][name]["commit_base"] = get_commit_hash("HEAD")

    save_state(state)
    return initialized_repo
```

### Helper function for running `gs` commands in tests

```python
def run_gs(*args, cwd=None):
    """Run a gs CLI command and return (returncode, stdout, stderr)."""
    from gitstacker.cli import main
    import sys
    from io import StringIO
    # ... or use subprocess for true isolation
```

## Dependencies
- Depends on: task-01 (atomic writes make tests deterministic)

## Acceptance Criteria
- [ ] `pytest --collect-only` discovers the test directories without errors
- [ ] `git_repo` fixture creates a valid git repo with `main` branch and initial commit
- [ ] `initialized_repo` fixture has `.git/gitstacker/state.json` present
- [ ] `stacked_repo` fixture has 3 branches in the stack with commits on each
- [ ] Fixtures properly use `monkeypatch.chdir()` so gitstacker operates in the temp repo
- [ ] `pytest tests/ -v` exits 0 (even if no tests yet — no collection errors)
- [ ] pytest-cov is configured and `pytest --cov=gitstacker` works

## Notes
- Use `monkeypatch.chdir()` rather than `os.chdir()` so the working directory is restored after each test.
- The `git_repo` fixture should configure `user.email` and `user.name` to avoid git prompting.
- Consider adding a fixture for a repo with a remote (bare repo) for sync tests.
- Each test gets its own `tmp_path` so tests are fully isolated.
