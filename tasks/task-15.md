# Task 15: Fix Submit Bugs (Force-Push Warning, PR Number=0) + Mocked Tests

## Description
Fix two bugs in the submit/github flow: (1) Bug #3: force-push without divergence check silently overwrites collaborator commits, and (2) Bug #10: `create_pr` returns PrInfo with number=0 when URL parsing fails. Add mocked integration tests for the submit command that don't require network access.

## Files to Create/Modify
- `gitstacker/github.py` — Fix Bug #10: raise error instead of returning number=0
- `gitstacker/commands/submit.py` — Fix Bug #3: add divergence check before force-push
- `gitstacker/git_ops.py` — Add `has_remote_diverged()` helper function
- `tests/integration/test_submit.py` — Mocked tests for submit command

## Implementation Details

### Fix Bug #10 in github.py

```python
def create_pr(
    title: str,
    body: str,
    base: str,
    head: str,
    draft: bool = False,
) -> PrInfo:
    """Create a new pull request."""
    args = [
        "pr", "create",
        "--title", title,
        "--body", body,
        "--base", base,
        "--head", head,
    ]
    if draft:
        args.append("--draft")

    result = gh(*args)
    if not result.success:
        raise RuntimeError(f"Failed to create PR: {result.stderr}")

    url = result.stdout.strip()

    # Try to fetch full PR info
    info = get_pr_for_branch(head)
    if info:
        return info

    # Fallback: parse URL for PR number
    import re
    match = re.search(r"/pull/(\d+)", url)
    if not match:
        raise RuntimeError(
            f"PR created but could not determine PR number from URL: {url}"
        )

    return PrInfo(
        number=int(match.group(1)),
        url=url,
        title=title,
        state="OPEN",
        base=base,
        head=head,
    )
```

### Fix Bug #3 in submit.py — Add divergence warning

Add to `git_ops.py`:
```python
def has_remote_diverged(branch: str) -> bool:
    """Check if remote branch has commits not in local branch.

    Returns True if remote has diverged (someone else pushed).
    """
    result = git("rev-list", "--count", f"{branch}..origin/{branch}")
    if not result.success:
        return False  # No remote branch yet
    return int(result.stdout) > 0
```

Update the push loop in `submit.py`:
```python
from ..git_ops import push_branch, has_remote_diverged

# Push all branches
info("Pushing branches to remote...")
for branch in stack["branches"]:
    sys.stdout.write(f"  {dim('push')} {branch}...")
    sys.stdout.flush()

    # Check for divergence before force-pushing
    if has_remote_diverged(branch):
        if "--force" not in args:
            print(f" {yellow('DIVERGED')}")
            warn(f'  Remote has new commits on "{branch}". Use --force to overwrite.')
            continue

    result = push_branch(branch, force=True)
    if result.success:
        print(f" {green('OK')}")
    else:
        print(f" {yellow('WARN')}: {result.stderr}")
```

### test_submit.py (mocked gh CLI)

```python
import pytest
from unittest.mock import patch, MagicMock
from gitstacker.commands.submit import cmd_submit
from gitstacker.commands.create import cmd_create
from gitstacker.commands.stack import cmd_stack
from gitstacker.git_ops import checkout
from gitstacker.store import load_state
from gitstacker.github import PrInfo, GhResult
import subprocess


def add_commit(repo, filename, content, message):
    (repo / filename).write_text(content)
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", message], cwd=repo, check=True)


class TestSubmitMocked:
    """Tests with mocked gh CLI — no network required."""

    @patch("gitstacker.commands.submit.is_gh_available", return_value=True)
    @patch("gitstacker.commands.submit.get_pr_for_branch", return_value=None)
    @patch("gitstacker.commands.submit.create_pr")
    @patch("gitstacker.commands.submit.push_branch")
    def test_submit_creates_prs(
        self, mock_push, mock_create, mock_get_pr, mock_gh, initialized_repo
    ):
        """Submit creates PRs for all branches."""
        cmd_stack(["new", "s"])
        cmd_create(["b1"])
        add_commit(initialized_repo, "f.txt", "x", "commit")

        mock_push.return_value = MagicMock(success=True)
        mock_create.return_value = PrInfo(
            number=1, url="https://github.com/org/repo/pull/1",
            title="B1", state="OPEN", base="main", head="b1"
        )

        cmd_submit([])
        mock_create.assert_called_once()

    @patch("gitstacker.commands.submit.is_gh_available", return_value=False)
    def test_submit_no_gh_errors(self, mock_gh, initialized_repo):
        """Submit without gh CLI errors."""
        with pytest.raises(SystemExit):
            cmd_submit([])

    @patch("gitstacker.commands.submit.is_gh_available", return_value=True)
    @patch("gitstacker.commands.submit.get_pr_for_branch")
    @patch("gitstacker.commands.submit.update_pr_base")
    @patch("gitstacker.commands.submit.update_pr")
    @patch("gitstacker.commands.submit.push_branch")
    def test_submit_updates_existing_pr_base(
        self, mock_push, mock_update, mock_update_base, mock_get_pr, mock_gh, initialized_repo
    ):
        """Submit updates PR base when parent changed."""
        cmd_stack(["new", "s"])
        cmd_create(["b1"])
        add_commit(initialized_repo, "f.txt", "x", "commit")

        mock_push.return_value = MagicMock(success=True)
        mock_get_pr.return_value = PrInfo(
            number=42, url="https://github.com/org/repo/pull/42",
            title="B1", state="OPEN", base="old-parent", head="b1"
        )

        cmd_submit([])
        mock_update_base.assert_called_once_with(42, "main")

    @patch("gitstacker.commands.submit.is_gh_available", return_value=True)
    @patch("gitstacker.commands.submit.push_branch")
    @patch("gitstacker.commands.submit.get_pr_for_branch", return_value=None)
    @patch("gitstacker.commands.submit.create_pr")
    def test_submit_draft_flag(
        self, mock_create, mock_get_pr, mock_push, mock_gh, initialized_repo
    ):
        """--draft flag is passed to create_pr."""
        cmd_stack(["new", "s"])
        cmd_create(["b1"])
        add_commit(initialized_repo, "f.txt", "x", "commit")

        mock_push.return_value = MagicMock(success=True)
        mock_create.return_value = PrInfo(
            number=1, url="url", title="B1", state="OPEN", base="main", head="b1"
        )

        cmd_submit(["--draft"])
        _, kwargs = mock_create.call_args
        assert kwargs.get("draft") is True or mock_create.call_args[1].get("draft") is True


class TestCreatePrValidation:
    """Tests for Bug #10 fix."""

    @patch("gitstacker.github.gh")
    @patch("gitstacker.github.get_pr_for_branch", return_value=None)
    def test_create_pr_raises_on_unparseable_url(self, mock_get, mock_gh):
        """create_pr raises instead of returning number=0."""
        from gitstacker.github import create_pr
        mock_gh.return_value = GhResult(
            stdout="some-garbage-not-a-url", stderr="", returncode=0
        )
        with pytest.raises(RuntimeError, match="could not determine PR number"):
            create_pr(title="T", body="B", base="main", head="b1")

    @patch("gitstacker.github.gh")
    @patch("gitstacker.github.get_pr_for_branch", return_value=None)
    def test_create_pr_parses_url_correctly(self, mock_get, mock_gh):
        """create_pr extracts number from valid URL."""
        from gitstacker.github import create_pr
        mock_gh.return_value = GhResult(
            stdout="https://github.com/org/repo/pull/99", stderr="", returncode=0
        )
        pr = create_pr(title="T", body="B", base="main", head="b1")
        assert pr.number == 99
```

## Dependencies
- Depends on: task-02 (test infrastructure)

## Acceptance Criteria
- [ ] Bug #10: `create_pr` raises RuntimeError instead of returning `number=0`
- [ ] Bug #10: Valid PR URLs are still parsed correctly
- [ ] Bug #3: Diverged branches show warning and skip push (unless --force)
- [ ] Bug #3: `--force` flag overrides divergence check
- [ ] Submit tests use mocked `gh` CLI — no network required
- [ ] Tests verify: PR creation, PR base update, draft flag, error on no gh
- [ ] `has_remote_diverged()` utility function added to git_ops.py
- [ ] `pytest tests/integration/test_submit.py -v` passes all tests
- [ ] At least 6 test cases

## Notes
- All submit tests mock `gh` CLI calls — we never call GitHub for real.
- `has_remote_diverged` uses `git rev-list --count branch..origin/branch` to detect remote-only commits.
- The `--force` flag on submit means "I know remote diverged, push anyway". This is different from git's `--force`.
- Mock at the function level (`patch("gitstacker.commands.submit.create_pr")`) not at subprocess level.
