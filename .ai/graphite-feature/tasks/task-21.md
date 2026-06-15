# Task 21: Refactor Restack Internals — Extract `restack_from()`

## Description
Extract the core rebase loop from `cmd_restack()` into a reusable `restack_from()` function. This allows `gs modify` to restack only the branches above the modified branch without duplicating the rebase logic.

## Dependencies
- None (refactoring existing code)

## Affected Files
- `gitstacker/commands/restack.py` — extract function, refactor `cmd_restack` to call it

## Implementation Details

### Extract `restack_from()` function

Add this function to `restack.py` (above `cmd_restack`):

```python
def restack_from(state: dict, stack: dict, start_index: int = 0,
                 skip_frozen: bool = True) -> tuple[bool, str, list[str]]:
    """Restack branches starting from start_index in the given stack.
    
    Args:
        state: Current gitstacker state dict.
        stack: Stack dict containing the branches to rebase.
        start_index: Index in stack["branches"] to start from (inclusive).
        skip_frozen: If True, skip branches marked as frozen.
    
    Returns:
        Tuple of (all_succeeded: bool, failed_branch: str, successfully_rebased: list[str])
        If all_succeeded is True, failed_branch is empty string.
    """
    branches = stack["branches"]
    branch_count = len(branches)
    successfully_rebased = []
    
    for i in range(start_index, branch_count):
        branch = branches[i]
        meta = state["branches"].get(branch, {})
        
        # Skip frozen branches
        if skip_frozen and meta.get("frozen", False):
            idx_display = dim(f"[{i + 1}/{branch_count}]")
            print(f"  {idx_display} Skipping {bold(branch)} (frozen)")
            continue
        
        parent = get_parent_branch(state, stack, branch)
        old_base = meta.get("commit_base") or parent
        
        idx_display = dim(f"[{i + 1}/{branch_count}]")
        sys.stdout.write(f"  {idx_display} Rebasing {bold(branch)} onto {parent}...")
        sys.stdout.flush()
        
        # Perform rebase --onto
        result = rebase_onto(parent, old_base, branch)
        
        if not result.success:
            print(f" {red('CONFLICT')}")
            rebase_abort()
            
            # Try simple rebase as fallback
            sys.stdout.write(f"  {dim('  Trying simple rebase...')}")
            sys.stdout.flush()
            
            simple_result = git("rebase", parent, branch)
            if simple_result.success:
                print(f" {green('OK')}")
                successfully_rebased.append(branch)
                if branch in state["branches"]:
                    state["branches"][branch]["commit_base"] = get_commit_hash(parent)
            else:
                print(f" {red('CONFLICT')}")
                rebase_abort()
                return (False, branch, successfully_rebased)
        else:
            print(f" {green('OK')}")
            successfully_rebased.append(branch)
            if branch in state["branches"]:
                state["branches"][branch]["commit_base"] = get_commit_hash(parent)
    
    return (True, "", successfully_rebased)
```

### Refactor `cmd_restack()` to use `restack_from()`

Replace the for-loop in `cmd_restack()` (lines 57-98) with a call to `restack_from()`:

```python
    # Replace the manual loop with:
    all_ok, failed_branch, successfully_rebased = restack_from(state, stack, start_index=0)
    
    # Store or clear restack progress (same logic as before)
    if not all_ok:
        state["_restack_progress"] = {
            "stack": stack["name"],
            "failed_at": failed_branch,
            "completed": successfully_rebased,
            "original_branch": current_branch,
        }
    else:
        state.pop("_restack_progress", None)
```

### Also refactor `_restack_continue()` similarly

Replace the for-loop in `_restack_continue()` (lines 203-238) with:
```python
    all_ok, failed_at, newly_rebased = restack_from(state, stack, start_index=continue_idx)
```

And update the progress tracking logic to use these return values.

### Important: Preserve exact existing behavior
- The output format (index display, OK/CONFLICT) must be identical
- The commit_base update logic must be identical  
- The fallback from `rebase --onto` to simple `rebase` must be preserved
- The only NEW behavior is the `skip_frozen` parameter (which defaults to True but has no effect yet since no branches are frozen)

## Acceptance Criteria
- [ ] `restack_from()` function exists and is importable from `gitstacker.commands.restack`
- [ ] `restack_from()` accepts `start_index` parameter to begin from any point in the stack
- [ ] `restack_from()` accepts `skip_frozen` parameter (defaults to True)
- [ ] `restack_from()` returns `(success_bool, failed_branch_name, rebased_list)`
- [ ] `cmd_restack()` uses `restack_from()` internally (no duplicated rebase logic)
- [ ] `_restack_continue()` uses `restack_from()` for the continuation loop
- [ ] All existing restack tests still pass (`pytest tests/integration/test_restack.py`)
- [ ] Output format is unchanged from user's perspective
- [ ] `restack_from()` updates `commit_base` in state for successfully rebased branches
