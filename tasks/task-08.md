# Task 08: Fix Restack Bugs

## Description
Fix two bugs in `restack.py`: (1) partial state save on restack failure — currently state is saved even for the failed branch, and (2) stash pop on rebased branch may silently conflict. The restack command should only persist state for successfully rebased branches and warn before popping stash after a rebase.

## Files to Create/Modify
- `gitstacker/commands/restack.py` — Fix partial state save and stash pop safety

## Implementation Details

### Fix 1: Partial State Save (Bug #12)
Currently at line 96, `save_state(state)` is called even when `failed=True`, which saves the state including updates for the branch that failed. The fix tracks which branches were successfully rebased:

```python
def cmd_restack(args: list[str]) -> None:
    state = load_state()
    current_branch = get_current_branch()

    # ... (find stack, check working tree — unchanged) ...

    failed = False
    failed_branch = ""
    successfully_rebased = []  # Track successful branches

    for i, branch in enumerate(stack["branches"]):
        parent = get_parent_branch(state, stack, branch)
        meta = state["branches"].get(branch, {})
        old_base = meta.get("commit_base") or parent

        # ... (display logic unchanged) ...

        result = rebase_onto(parent, old_base, branch)

        if not result.success:
            # ... (abort and try simple rebase — unchanged) ...

            simple_result = git("rebase", parent, branch)
            if simple_result.success:
                print(f" {green('OK')}")
                successfully_rebased.append(branch)
                if branch in state["branches"]:
                    state["branches"][branch]["commit_base"] = get_commit_hash(parent)
            else:
                print(f" {red('CONFLICT')}")
                rebase_abort()
                failed = True
                failed_branch = branch
                # DON'T update state for this branch
                break
        else:
            print(f" {green('OK')}")
            successfully_rebased.append(branch)
            if branch in state["branches"]:
                state["branches"][branch]["commit_base"] = get_commit_hash(parent)

    # Always save state (only successfully rebased branches were updated)
    save_state(state)

    if not failed:
        print()
        success("Stack restacked successfully!")
    else:
        print()
        warn(f'Restacking stopped at "{failed_branch}" due to conflicts.')
        info(f"Successfully rebased: {len(successfully_rebased)}/{len(stack['branches'])} branches")
        info("Resolve conflicts manually, then run `gs restack` again.")
```

### Fix 2: Stash Pop Safety (Bug #5)
After a rebase, the working tree has changed. If stash was pushed before rebase, popping it may conflict. Check for conflict and warn:

```python
    # Pop stash safely
    if did_stash:
        info("Restoring stashed changes...")
        pop_result = git("stash", "pop")
        if not pop_result.success:
            warn("Could not automatically restore stashed changes.")
            info("Your changes are still in the stash. Run `git stash pop` manually.")
            info(f"Stash error: {pop_result.stderr}")
```

Replace the bare `stash_pop()` call with this safer version that uses `git()` directly to check the result.

### Additional: Save restack progress for `--continue` (prep for Task 14)
Store which branch failed in state for later continuation:

```python
    if failed:
        state["_restack_progress"] = {
            "stack": stack["name"],
            "failed_at": failed_branch,
            "completed": successfully_rebased,
            "original_branch": current_branch,
        }
    else:
        state.pop("_restack_progress", None)
    save_state(state)
```

## Dependencies
- Depends on: task-01 (atomic state writes)

## Acceptance Criteria
- [ ] On restack failure, only successfully rebased branches have their `commit_base` updated
- [ ] The failed branch's `commit_base` is NOT updated in state
- [ ] State is saved after failure (so successful rebases aren't lost)
- [ ] Stash pop failure shows a warning instead of silently failing or crashing
- [ ] User is told their changes are still in the stash
- [ ] `_restack_progress` metadata is stored on failure for `--continue` support
- [ ] `_restack_progress` is cleared on successful restack
- [ ] Original branch checkout still works after failed restack

## Notes
- The key insight for Bug #12: the current code updates `state["branches"][branch]["commit_base"]` in the loop, so by the time `save_state` is called on failure, partially-updated state is persisted. The fix ensures we only update state for branches that completed.
- For Bug #5: `git stash pop` can fail with merge conflicts, leaving the stash entry intact. The user needs to resolve manually.
- The `_restack_progress` key is prefixed with `_` to indicate internal metadata. It's used by `--continue` in Task 14.
