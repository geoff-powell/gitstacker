# Task 14: Implement `gs restack --continue` + Tests

## Description
Implement the `--continue` flag for `gs restack` that allows users to resume restacking after resolving conflicts. When a restack fails at a branch, the progress is saved (from Task 08). `--continue` skips already-completed branches and continues from the failed one.

## Files to Create/Modify
- `gitstacker/commands/restack.py` — Add `--continue` flag handling
- `tests/integration/test_restack.py` — Add tests for `--continue` flow

## Implementation Details

### Update cmd_restack in restack.py

```python
def cmd_restack(args: list[str]) -> None:
    is_continue = "--continue" in args

    state = load_state()
    current_branch = get_current_branch()

    if is_continue:
        return _restack_continue(state, current_branch)

    # ... rest of existing restack logic ...


def _restack_continue(state: dict, current_branch: str) -> None:
    """Continue a previously failed restack from where it left off."""
    progress = state.get("_restack_progress")
    if not progress:
        error("No restack in progress. Run `gs restack` to start.")
        raise SystemExit(1)

    stack_name = progress["stack"]
    stack = state["stacks"].get(stack_name)
    if not stack:
        error(f'Stack "{stack_name}" not found. Clearing progress.')
        state.pop("_restack_progress", None)
        save_state(state)
        raise SystemExit(1)

    failed_branch = progress["failed_at"]
    completed = progress.get("completed", [])
    original_branch = progress.get("original_branch", current_branch)

    # Check that we're on the failed branch (user should have resolved conflicts)
    if current_branch != failed_branch:
        warn(f'Expected to be on "{failed_branch}" (the branch with conflicts).')
        info(f"Switch to it and resolve conflicts first: git checkout {failed_branch}")
        raise SystemExit(1)

    # Check for ongoing rebase
    from ..git_ops import git
    rebase_in_progress = git("rebase", "--show-current-patch")
    if rebase_in_progress.success:
        # There's still a rebase in progress — user needs to finish it
        error("A rebase is still in progress. Complete it first:")
        info("  git rebase --continue  (after resolving conflicts)")
        info("  git rebase --abort     (to cancel)")
        raise SystemExit(1)

    info(f"Continuing restack from {bold(failed_branch)}...")
    print()

    # Find the index to continue from (the branch AFTER the failed one)
    branches = stack["branches"]
    try:
        continue_idx = branches.index(failed_branch) + 1
    except ValueError:
        error(f'Branch "{failed_branch}" no longer in stack.')
        state.pop("_restack_progress", None)
        save_state(state)
        raise SystemExit(1)

    # Update commit_base for the branch that was manually resolved
    if failed_branch in state["branches"]:
        parent = get_parent_branch(state, stack, failed_branch)
        state["branches"][failed_branch]["commit_base"] = get_commit_hash(parent)

    # Continue restacking remaining branches
    branch_count = len(branches)
    failed = False
    failed_at = ""

    for i in range(continue_idx, branch_count):
        branch = branches[i]
        parent = get_parent_branch(state, stack, branch)
        meta = state["branches"].get(branch, {})
        old_base = meta.get("commit_base") or parent

        idx_display = dim(f"[{i + 1}/{branch_count}]")
        sys.stdout.write(f"  {idx_display} Rebasing {bold(branch)} onto {parent}...")
        sys.stdout.flush()

        result = rebase_onto(parent, old_base, branch)

        if not result.success:
            rebase_abort()
            simple_result = git("rebase", parent, branch)
            if simple_result.success:
                print(f" {green('OK')}")
                if branch in state["branches"]:
                    state["branches"][branch]["commit_base"] = get_commit_hash(parent)
            else:
                print(f" {red('CONFLICT')}")
                rebase_abort()
                failed = True
                failed_at = branch
                break
        else:
            print(f" {green('OK')}")
            if branch in state["branches"]:
                state["branches"][branch]["commit_base"] = get_commit_hash(parent)

    if failed:
        state["_restack_progress"] = {
            "stack": stack_name,
            "failed_at": failed_at,
            "completed": completed + [failed_branch] + branches[continue_idx:branches.index(failed_at)],
            "original_branch": original_branch,
        }
        save_state(state)
        warn(f'Restacking stopped at "{failed_at}" due to conflicts.')
        info("Resolve conflicts, then run `gs restack --continue`.")
    else:
        state.pop("_restack_progress", None)
        save_state(state)
        print()
        success("Stack restacked successfully!")

    # Return to original branch
    try:
        checkout(original_branch)
    except Exception:
        pass
```

### CLI registration

In `cli.py`, the existing routing already passes `command_args` to `cmd_restack`, so `--continue` will be in `args`. No CLI change needed.

### Integration tests (add to test_restack.py)

```python
class TestRestackContinue:
    def test_continue_no_progress_errors(self, stacked_repo):
        """--continue with no prior failure errors."""
        checkout("branch-1")
        with pytest.raises(SystemExit):
            cmd_restack(["--continue"])

    def test_continue_after_resolved_conflict(self, initialized_repo):
        """After resolving conflict, --continue finishes remaining branches."""
        # Setup: create conflict scenario
        cmd_stack(["new", "s"])
        cmd_create(["b1"])
        add_commit(initialized_repo, "conflict.txt", "b1 version", "B1")
        cmd_create(["b2"])
        add_commit(initialized_repo, "b2.txt", "b2 content", "B2")
        cmd_create(["b3"])
        add_commit(initialized_repo, "b3.txt", "b3 content", "B3")

        # Cause conflict on b1
        checkout("main")
        add_commit(initialized_repo, "conflict.txt", "TRUNK version", "Trunk conflict")

        # First restack fails
        checkout("b1")
        cmd_restack([])

        state = load_state()
        # Verify progress was saved
        assert "_restack_progress" in state

    def test_continue_wrong_branch_errors(self, stacked_repo):
        """--continue on wrong branch shows helpful error."""
        # Manually set progress
        state = load_state()
        state["_restack_progress"] = {
            "stack": "test-stack",
            "failed_at": "branch-2",
            "completed": ["branch-1"],
            "original_branch": "branch-2",
        }
        from gitstacker.store import save_state
        save_state(state)

        checkout("branch-1")  # Wrong branch
        with pytest.raises(SystemExit):
            cmd_restack(["--continue"])
```

## Dependencies
- Depends on: task-08 (restack progress tracking), task-09 (restack tests for context)

## Acceptance Criteria
- [ ] `gs restack --continue` resumes from the failed branch
- [ ] Skips already-completed branches
- [ ] Errors if no restack progress exists
- [ ] Errors if user is on wrong branch (not the conflict branch)
- [ ] Updates commit_base for the manually-resolved branch
- [ ] Clears `_restack_progress` on successful completion
- [ ] If another conflict is hit, saves new progress state
- [ ] Returns to original branch on completion
- [ ] `pytest tests/integration/test_restack.py -v` passes (existing + new tests)
- [ ] At least 3 new test cases for --continue

## Notes
- The user workflow is: `gs restack` → conflict → resolve manually → `git add . && git rebase --continue` → `gs restack --continue`
- Detecting ongoing rebase: check for `.git/rebase-merge` or `.git/rebase-apply` directory, or use `git rebase --show-current-patch`.
- The `_restack_progress` state key was added in Task 08.
