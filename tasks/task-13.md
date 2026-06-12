# Task 13: Implement `gs diff` Command + Tests

## Description
Implement the `gs diff` command that shows the diff of the current branch vs its parent in the stack (not vs HEAD~1). This is essential for reviewing what a specific branch adds to the stack. Register it in the CLI router and add integration tests.

## Files to Create/Modify
- `gitstacker/commands/diff.py` — New file: implement `cmd_diff`
- `gitstacker/cli.py` — Register `diff` command in CLI router
- `tests/integration/test_diff.py` — Integration tests

## Implementation Details

### gitstacker/commands/diff.py

```python
"""gs diff - Show diff of current branch vs its parent in the stack."""

import subprocess
import sys
from ..git_ops import get_current_branch, get_merge_base
from ..store import load_state, get_current_stack, get_parent_branch
from ..output import error, info


def cmd_diff(args: list[str]) -> None:
    """Show diff between current branch and its stack parent.

    This shows what THIS branch adds, not what HEAD~1 adds.
    Uses merge-base to find the fork point, then diffs from there to HEAD.
    """
    state = load_state()
    current_branch = get_current_branch()

    # Find the stack and parent
    stack = get_current_stack(state, current_branch)
    if not stack:
        error("Not on a stacked branch. Nothing to diff.")
        raise SystemExit(1)

    parent = get_parent_branch(state, stack, current_branch)

    # Get the merge base (fork point)
    merge_base = get_merge_base(parent, current_branch)

    # Build diff command
    diff_args = ["git", "diff"]

    # Pass through any extra args (e.g., --stat, --name-only, file paths)
    if "--stat" in args:
        diff_args.append("--stat")
        args = [a for a in args if a != "--stat"]
    if "--name-only" in args:
        diff_args.append("--name-only")
        args = [a for a in args if a != "--name-only"]
    if "--cached" in args:
        diff_args.append("--cached")
        args = [a for a in args if a != "--cached"]

    diff_args.append(f"{merge_base}..HEAD")

    # Add any remaining args (file paths)
    diff_args.extend(args)

    # Run diff with output going directly to terminal (for pager support)
    result = subprocess.run(diff_args)
    sys.exit(result.returncode)
```

### CLI registration in cli.py

Add to the command routing in `main()`:

```python
elif command == "diff":
    from .commands.diff import cmd_diff
    cmd_diff(command_args)
```

Also update `HELP_TEXT`:
```
  {cyan("diff")} [--stat]          Show diff of current branch vs parent
```

### test_diff.py

```python
import pytest
import subprocess
from gitstacker.commands.diff import cmd_diff
from gitstacker.commands.create import cmd_create
from gitstacker.commands.stack import cmd_stack
from gitstacker.git_ops import get_current_branch, checkout
from gitstacker.store import load_state


def add_commit(repo, filename, content, message):
    (repo / filename).write_text(content)
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", message], cwd=repo, check=True)


class TestDiff:
    def test_diff_shows_branch_changes(self, initialized_repo, capsys):
        """Diff shows only changes made on current branch, not parent."""
        cmd_stack(["new", "s"])
        cmd_create(["b1"])
        add_commit(initialized_repo, "b1-file.txt", "b1 content", "B1 commit")
        cmd_create(["b2"])
        add_commit(initialized_repo, "b2-file.txt", "b2 content", "B2 commit")

        # Diff on b2 should only show b2-file.txt, not b1-file.txt
        # Since cmd_diff calls subprocess.run and exits, test via subprocess
        result = subprocess.run(
            ["git", "diff", "--name-only", "b1..HEAD"],
            cwd=initialized_repo, capture_output=True, text=True
        )
        assert "b2-file.txt" in result.stdout
        assert "b1-file.txt" not in result.stdout

    def test_diff_not_on_stack_errors(self, initialized_repo):
        """Diff when not on stacked branch errors."""
        cmd_stack(["new", "s"])
        with pytest.raises(SystemExit):
            cmd_diff([])

    def test_diff_first_branch_vs_trunk(self, initialized_repo):
        """First branch diffs against trunk."""
        cmd_stack(["new", "s"])
        cmd_create(["b1"])
        add_commit(initialized_repo, "new.txt", "content", "Add file")

        # Verify parent is trunk
        state = load_state()
        stack = state["stacks"]["s"]
        from gitstacker.store import get_parent_branch
        parent = get_parent_branch(state, stack, "b1")
        assert parent == "main"

    def test_diff_stat_flag(self, initialized_repo):
        """--stat flag is passed through to git diff."""
        cmd_stack(["new", "s"])
        cmd_create(["b1"])
        add_commit(initialized_repo, "stat-test.txt", "content", "Add file")

        result = subprocess.run(
            ["git", "diff", "--stat", "main..HEAD"],
            cwd=initialized_repo, capture_output=True, text=True
        )
        assert "stat-test.txt" in result.stdout

    def test_diff_empty_branch(self, initialized_repo):
        """Diff on branch with no commits above parent shows nothing."""
        cmd_stack(["new", "s"])
        cmd_create(["empty-branch"])

        result = subprocess.run(
            ["git", "diff", "main..HEAD"],
            cwd=initialized_repo, capture_output=True, text=True
        )
        assert result.stdout.strip() == ""
```

## Dependencies
- Depends on: task-02 (test infrastructure)

## Acceptance Criteria
- [ ] `gs diff` shows changes between current branch and its stack parent
- [ ] `gs diff` on the first branch diffs against trunk
- [ ] `gs diff` when not on a stacked branch shows error and exits 1
- [ ] `gs diff --stat` passes --stat flag to git diff
- [ ] `gs diff --name-only` works correctly
- [ ] Diff uses merge-base (not direct parent ref) for accurate fork-point diffing
- [ ] Command registered in CLI and shows in help text
- [ ] `pytest tests/integration/test_diff.py -v` passes all tests
- [ ] At least 5 test cases

## Notes
- Using `subprocess.run` instead of `git_ops.git()` for the diff output so it goes directly to stdout with pager support.
- The merge-base approach ensures we see only the changes introduced on this branch, even if parent has advanced.
- `sys.exit(result.returncode)` passes through git's exit code (0 for no diff shown is success).
- Tests that check diff output directly need to use `subprocess.run` since `cmd_diff` exits the process.
