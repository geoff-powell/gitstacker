# Task 20: Add Journal Snapshots to Existing Mutating Commands

## Description
Wire `journal.snapshot_before()` into all existing mutating commands so that `gs undo` has entries to restore. Each mutating command should call `snapshot_before(operation_name, state)` immediately after loading state and before performing any mutations.

## Dependencies
- Task 18 (journal.py must exist)

## Affected Files
- `gitstacker/commands/create.py` — add snapshot call
- `gitstacker/commands/delete.py` — add snapshot call
- `gitstacker/commands/restack.py` — add snapshot call
- `gitstacker/commands/sync.py` — add snapshot call
- `gitstacker/commands/stack.py` — add snapshot call (in `stack_delete` only)

## Implementation Details

### Pattern for each file

Add this import at the top (alongside existing imports):
```python
from ..journal import snapshot_before
```

Then call `snapshot_before(op, state)` **after** `load_state()` but **before** any mutations.

### `gitstacker/commands/create.py`

After the line that calls `load_state()`, add:
```python
    state = load_state()
    snapshot_before("create", state)  # <-- ADD THIS
    # ... rest of create logic
```

### `gitstacker/commands/delete.py`

After `load_state()`, before any branch removal:
```python
    state = load_state()
    snapshot_before("delete", state)  # <-- ADD THIS
    # ... rest of delete logic
```

### `gitstacker/commands/restack.py`

In `cmd_restack()`, after `load_state()` and before the rebase loop. Only snapshot for a fresh restack (not `--continue`):
```python
    state = load_state()
    current_branch = get_current_branch()

    if is_continue:
        return _restack_continue(state, current_branch)

    # Snapshot for undo (only on fresh restack, not --continue)
    from ..journal import snapshot_before
    snapshot_before("restack", state)

    # ... rest of restack logic
```

### `gitstacker/commands/sync.py`

After `load_state()`, before fetch/pull operations:
```python
    state = load_state()
    snapshot_before("sync", state)  # <-- ADD THIS
    # ... rest of sync logic
```

### `gitstacker/commands/stack.py`

Only in the `stack_delete` sub-command handler. Find where state is loaded before deletion and add:
```python
    state = load_state()
    snapshot_before("stack_delete", state)  # <-- ADD THIS
    # ... delete logic
```

### Commands that should NOT snapshot:
- `init` — no prior state to restore
- `log`, `status`, `diff` — read-only
- `navigate` (up/down/top/bottom) — only moves HEAD, no state mutation
- `trunk` — rarely used, optional (can add later)
- `submit` — pushes to remote, can't be undone locally anyway
- `completions` — read-only

## Acceptance Criteria
- [ ] `gs create` records a journal entry before creating a branch
- [ ] `gs delete` records a journal entry before removing a branch
- [ ] `gs restack` records a journal entry before rebasing (not on `--continue`)
- [ ] `gs sync` records a journal entry before syncing
- [ ] `gs stack delete` records a journal entry before deleting a stack
- [ ] After running any of these commands, `journal.json` contains an entry with the correct operation name
- [ ] Journal entries contain valid pre_state, branch_shas, head_branch, head_sha
- [ ] Read-only commands (`gs log`, `gs status`, `gs diff`) do NOT create journal entries
- [ ] No import errors or circular dependencies introduced
