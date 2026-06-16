# Plan: `gs modify`, `gs undo`, and Collaboration Commands

## Summary

Add three feature sets to GitStacker inspired by Graphite CLI: (1) `gs modify` for amending/committing to a branch and auto-restacking upstack, (2) `gs undo` as a safety net to revert mutating operations, and (3) collaboration commands (`gs get`, `gs freeze`, `gs unfreeze`) to enable teams to work on shared stacks.

---

## Architecture Decisions

### 1. Undo Journal Design

- **Location:** `.git/gitstacker/journal.json` — separate from `state.json` to avoid bloating the core state file
- **Format:** Array of operation entries (max 10), newest first
- **Each entry stores:**
  - `operation`: command name (e.g., "modify", "create", "delete", "restack", "sync")
  - `timestamp`: ISO 8601 string
  - `pre_state`: full snapshot of `state.json` before the operation
  - `branch_shas`: `dict[str, str]` mapping every tracked branch name → commit SHA at time of snapshot
  - `head_branch`: which branch the user was on
  - `head_sha`: SHA of HEAD at time of snapshot
- **Undo restores both state.json AND git branch positions** using `git branch -f <name> <sha>` + `git checkout <original_head>`
- **Journal is NOT undone itself** — after undo, the journal records the undo operation as a new entry (so you can undo an undo)
- **New module:** `gitstacker/journal.py` handles all journal I/O

### 2. Modify → Restack Pipeline

- `gs modify` performs the git commit operation (amend or new commit), then calls the existing restack logic for branches above the modified point
- **Reuses `restack.py` internals** — extract a `restack_from(state, stack, start_index)` function that both `cmd_restack` and `cmd_modify` can call
- **Conflict handling mirrors restack** — saves `_restack_progress` and supports `gs modify --continue` (alias for `gs restack --continue`)
- The `--into <branch>` flag requires checking out the target branch, applying changes there, then restacking from that point

### 3. Freeze State Storage

- **Stored in branch metadata** in `state.json` — add `"frozen": bool` field to each branch entry (default `false`)
- **Not a separate data structure** — keeps the schema simple and the freeze status travels with the branch metadata
- **Enforcement points:** `cmd_create` (can't create on frozen parent), `cmd_modify` (can't modify frozen branch), and `restack` (skip frozen branches)
- **Validation in `_validate_state()`** adds `meta.setdefault("frozen", False)` for backward compatibility

### 4. `gs get` Remote Stack Detection

- Fetches branch from remote, then inspects PR metadata via `gh pr view` to find the PR's base branch
- Recursively walks down the PR base chain until hitting trunk to reconstruct the full stack
- Alternatively, if branches follow naming conventions or state is shared, detect from branch metadata
- Registers discovered stack in local state and checks out all branches

### 5. Snapshot Placement (Pre-operation Hook)

- Rather than a decorator or middleware (overkill for if/elif dispatch), each mutating command calls `journal.snapshot_before(operation_name)` as its first action after loading state
- Mutating commands: `create`, `delete`, `modify`, `restack`, `sync`, `stack delete`
- Non-mutating commands (log, status, diff, navigate) do NOT snapshot

---

## Data Model Changes

### `state.json` Schema Additions

```jsonc
{
  "branches": {
    "branch-name": {
      "name": "branch-name",
      "parent": "main",
      "pr_number": null,
      "pr_url": null,
      "commit_base": "abc123...",
      "frozen": false          // NEW: freeze status
    }
  }
  // ... rest unchanged
}
```

### New File: `.git/gitstacker/journal.json`

```jsonc
[
  {
    "operation": "modify",
    "timestamp": "2026-06-12T10:30:00",
    "pre_state": { /* full state.json snapshot */ },
    "branch_shas": {
      "branch-1": "abc123...",
      "branch-2": "def456...",
      "branch-3": "789abc..."
    },
    "head_branch": "branch-1",
    "head_sha": "abc123..."
  }
  // ... up to 10 entries
]
```

---

## Affected Modules

| Module | Type | Changes |
|--------|------|---------|
| `gitstacker/journal.py` | **new** | Undo journal I/O: snapshot, restore, prune |
| `gitstacker/commands/modify.py` | **new** | `gs modify` command implementation |
| `gitstacker/commands/undo.py` | **new** | `gs undo` command implementation |
| `gitstacker/commands/get.py` | **new** | `gs get <branch>` command implementation |
| `gitstacker/commands/freeze.py` | **new** | `gs freeze` and `gs unfreeze` commands |
| `gitstacker/commands/restack.py` | modified | Extract `restack_from()` helper; respect frozen branches |
| `gitstacker/cli.py` | modified | Add dispatch entries for modify, undo, get, freeze, unfreeze |
| `gitstacker/store.py` | modified | Add `frozen` default in `_validate_state()`; add `is_branch_frozen()` helper |
| `gitstacker/git_ops.py` | modified | Add `amend_commit()`, `stage_all()`, `get_all_branch_shas()`, `reset_branch()` helpers |
| `gitstacker/commands/create.py` | modified | Check frozen status of parent before creating |
| `gitstacker/commands/completions.py` | modified | Add completions for new commands |
| `gitstacker/output.py` | modified | Add `frozen` indicator symbol (e.g., snowflake or lock icon) |
| `tests/integration/test_modify.py` | **new** | Tests for modify + auto-restack |
| `tests/integration/test_undo.py` | **new** | Tests for undo/journal |
| `tests/integration/test_freeze.py` | **new** | Tests for freeze/unfreeze |
| `tests/integration/test_get.py` | **new** | Tests for get (mocked gh) |

---

## Implementation Approach

### Step 1: Journal Infrastructure (`journal.py`)

Create the undo journal module with these functions:

```python
# gitstacker/journal.py

JOURNAL_FILE = "journal.json"
MAX_ENTRIES = 10

def _get_journal_path() -> str: ...
def load_journal() -> list[dict]: ...
def save_journal(entries: list[dict]) -> None: ...  # atomic write

def snapshot_before(operation: str, state: dict) -> None:
    """Capture pre-operation state + all branch SHAs. Call at start of mutating ops."""

def get_last_entry() -> Optional[dict]:
    """Get most recent journal entry for undo."""

def restore_entry(entry: dict) -> None:
    """Restore state.json and reset all branches to saved SHAs."""
```

The `snapshot_before` function:
1. Loads current journal
2. Captures `state` (deep copy), all branch SHAs via `git rev-parse`, current HEAD info
3. Prepends entry to journal list
4. Truncates to `MAX_ENTRIES`
5. Saves journal atomically

### Step 2: `gs undo` Command

```python
# gitstacker/commands/undo.py

def cmd_undo(args: list[str]) -> None:
    1. Warn if working tree is dirty (uncommitted changes would be lost)
    2. Load journal, get last entry
    3. Error if no entries ("Nothing to undo")
    4. Show what will be undone: "Undo <operation> from <timestamp>?"
    5. Restore state.json from entry's pre_state
    6. For each branch in entry's branch_shas:
       - git branch -f <name> <sha> (reset branch pointer)
    7. git checkout <entry.head_branch> (return to original position)
    8. Remove the consumed entry from journal
    9. Print success with details
```

### Step 3: Refactor Restack Internals

Extract from `cmd_restack`:

```python
def restack_from(state: dict, stack: dict, start_index: int = 0, 
                 skip_frozen: bool = True) -> tuple[bool, str]:
    """Restack branches starting from start_index.
    
    Returns (success: bool, failed_branch: str).
    Skips frozen branches if skip_frozen=True.
    """
```

This allows `cmd_modify` to call `restack_from(state, stack, modified_index + 1)` to only restack upstack branches.

### Step 4: `gs modify` Command

```python
# gitstacker/commands/modify.py

def cmd_modify(args: list[str]) -> None:
    # Parse flags
    amend = "--commit" not in args and "-c" not in args
    stage_all = "--all" in args or "-a" in args
    message = extract_flag_value(args, "--message", "-m")
    target_branch = extract_flag_value(args, "--into")
    is_continue = "--continue" in args

    if is_continue:
        # Delegate to restack --continue
        from .restack import cmd_restack
        return cmd_restack(["--continue"])

    state = load_state()
    current_branch = get_current_branch()
    
    # Determine target
    branch = target_branch or current_branch
    
    # Validate: branch must be in a stack
    stack = get_current_stack(state, branch)
    if not stack: error and exit
    
    # Validate: branch must not be frozen
    if state["branches"].get(branch, {}).get("frozen"):
        error("Branch is frozen. Unfreeze it first: gs unfreeze <branch>")
        exit
    
    # Snapshot for undo
    journal.snapshot_before("modify", state)
    
    # If --into, checkout target branch
    if target_branch and target_branch != current_branch:
        checkout(target_branch)
    
    # Stage changes
    if stage_all or (not amend):
        git("add", "-A")  # Stage all tracked changes
    # else: use whatever is already staged
    
    # Commit or amend
    if amend:
        cmd = ["commit", "--amend", "--no-edit"]
        if message:
            cmd = ["commit", "--amend", "-m", message]
    else:
        if not message:
            error("--message required with --commit")
            exit
        cmd = ["commit", "-m", message]
    
    result = git(*cmd)
    if not result.success:
        error(f"Commit failed: {result.stderr}")
        exit
    
    # Update commit_base for modified branch
    parent = get_parent_branch(state, stack, branch)
    state["branches"][branch]["commit_base"] = get_commit_hash(parent)
    
    # Restack everything above
    branch_pos = stack["branches"].index(branch)
    if branch_pos < len(stack["branches"]) - 1:
        restack_from(state, stack, start_index=branch_pos + 1)
    
    save_state(state)
    
    # Return to original branch if we moved
    if target_branch and target_branch != current_branch:
        checkout(current_branch)
```

### Step 5: Freeze/Unfreeze Commands

```python
# gitstacker/commands/freeze.py

def cmd_freeze(args: list[str]) -> None:
    state = load_state()
    branch = args[0] if args else get_current_branch()
    
    # Validate branch is tracked
    if branch not in state["branches"]:
        error(f'"{branch}" is not a stacked branch')
        exit
    
    if state["branches"][branch].get("frozen"):
        info(f'"{branch}" is already frozen')
        return
    
    state["branches"][branch]["frozen"] = True
    save_state(state)
    success(f'Froze "{branch}" — it will be skipped during restack/modify')


def cmd_unfreeze(args: list[str]) -> None:
    state = load_state()
    branch = args[0] if args else get_current_branch()
    
    if branch not in state["branches"]:
        error(f'"{branch}" is not a stacked branch')
        exit
    
    if not state["branches"][branch].get("frozen"):
        info(f'"{branch}" is not frozen')
        return
    
    state["branches"][branch]["frozen"] = False
    save_state(state)
    success(f'Unfroze "{branch}"')
```

### Step 6: `gs get` Command

```python
# gitstacker/commands/get.py

def cmd_get(args: list[str]) -> None:
    if not args:
        error("Branch name required: gs get <branch>")
        exit
    
    branch = args[0]
    state = load_state()
    
    # Fetch from remote
    info(f"Fetching {branch} from remote...")
    git_or_throw("fetch", "origin", branch)
    
    # Create local tracking branch
    if not branch_exists(branch):
        git_or_throw("checkout", "-b", branch, f"origin/{branch}")
    else:
        checkout(branch)
        git_or_throw("reset", "--hard", f"origin/{branch}")
    
    # Discover the stack via PR chain
    stack_branches = discover_stack_from_prs(branch, state["trunk"])
    
    # Fetch and create all discovered branches
    for b in stack_branches:
        if b == branch:
            continue
        if not branch_exists(b):
            git("fetch", "origin", b)
            git("checkout", "-b", b, f"origin/{b}")
    
    # Register stack in state
    stack_name = f"remote-{branch}"  # or derive from PR metadata
    if stack_name not in state["stacks"]:
        create_stack(state, stack_name, state["trunk"])
    
    for i, b in enumerate(stack_branches):
        parent = state["trunk"] if i == 0 else stack_branches[i-1]
        if b not in state["branches"]:
            add_branch_to_stack(state, stack_name, b, parent)
            state["branches"][b]["commit_base"] = get_commit_hash(parent)
    
    save_state(state)
    checkout(branch)
    success(f'Got stack: {" → ".join(stack_branches)}')


def discover_stack_from_prs(branch: str, trunk: str) -> list[str]:
    """Walk PR base chain to discover full stack ordering."""
    stack = []
    current = branch
    
    while current != trunk:
        stack.append(current)
        pr_info = get_pr_for_branch(current)
        if not pr_info:
            break
        current = pr_info.base
    
    stack.reverse()  # Bottom-up order
    return stack
```

### Step 7: Wire Up CLI Dispatch

Add to `cli.py`:
```python
elif command in ("modify", "m"):
    from .commands.modify import cmd_modify
    cmd_modify(command_args)

elif command == "undo":
    from .commands.undo import cmd_undo
    cmd_undo(command_args)

elif command == "get":
    from .commands.get import cmd_get
    cmd_get(command_args)

elif command == "freeze":
    from .commands.freeze import cmd_freeze
    cmd_freeze(command_args)

elif command == "unfreeze":
    from .commands.freeze import cmd_unfreeze
    cmd_unfreeze(command_args)
```

### Step 8: Add Snapshot Calls to Existing Mutating Commands

Add `journal.snapshot_before(op, state)` to:
- `cmd_create` — after `load_state()`, before `create_branch()`
- `cmd_delete` — after `load_state()`, before `remove_branch_from_stack()`
- `cmd_restack` — after `load_state()`, before the rebase loop
- `cmd_sync` — after `load_state()`, before `fetch_remote()`
- `stack_delete` — after `load_state()`, before `delete_stack()`

### Dependencies Between Steps

```
Step 1 (journal.py) ─── required by ──→ Step 2 (undo)
                    └── required by ──→ Step 8 (snapshot hooks in existing commands)
                    └── required by ──→ Step 4 (modify calls snapshot)

Step 3 (restack refactor) ── required by ──→ Step 4 (modify calls restack_from)
                         └── required by ──→ Step 5 (frozen skip in restack)

Step 5 (freeze) ── required by ──→ Step 4 (modify checks frozen)

Step 6 (get) ── independent, requires only github.py

Step 7 (CLI wiring) ── depends on all command files existing
```

**Recommended implementation order:**
1. Step 1 → Step 2 → Step 8 (undo is self-contained and useful immediately)
2. Step 3 → Step 5 → Step 4 (modify requires refactored restack + freeze)
3. Step 6 (get is independent)
4. Step 7 (wire everything up)

---

## Edge Cases and Error Handling

### `gs modify`
- **Nothing staged + no `--all`:** Error with helpful message ("No changes staged. Use -a to stage all or stage manually")
- **Amend on branch with no commits above parent:** Should work fine (amends the only commit)
- **`--into` targets a branch not in current stack:** Error with guidance
- **`--into` targets a branch above current position:** Warn that changes won't include current branch's commits
- **Conflict during auto-restack:** Save progress exactly like `gs restack` does; inform user to run `gs modify --continue`
- **Empty amend (no changes):** git will reject — surface the error clearly
- **Branch is frozen:** Block with clear error suggesting `gs unfreeze`

### `gs undo`
- **Dirty working tree:** Warn and abort ("Uncommitted changes would be lost. Commit or stash first.")
- **Branch was pushed to remote since snapshot:** Warn that undo is local-only; remote will diverge
- **Branch in snapshot no longer exists:** Skip it with warning; restore what we can
- **SHA in snapshot is unreachable (garbage collected):** Error with explanation; suggest `git reflog` 
- **Multiple rapid operations:** Each snapshot is independent; undo always reverts the latest one
- **Undo after undo:** Works — undo itself is journaled, so you can undo an undo (redo)
- **Journal file missing/corrupt:** Treat as empty; "Nothing to undo"

### `gs freeze`
- **Freeze trunk:** Block — trunk isn't a stacked branch
- **Freeze branch not in state:** Error with guidance
- **Restack with frozen branch in middle of stack:** Skip it but continue restacking branches above it (they rebase onto the frozen branch's current position)
- **Create on top of frozen branch:** Block with error explaining why
- **Modify --into frozen branch:** Block with error

### `gs get`
- **Branch doesn't exist on remote:** Clear error ("Branch not found on remote")
- **Branch already exists locally and is in a stack:** Warn about overwrite; require `--force`
- **No PR found for branch (can't discover stack):** Fall back to fetching just that single branch; register as single-branch stack
- **Circular PR base references:** Detect loops; bail with error
- **gh CLI not available:** Error with install instructions (same as submit)

---

## Acceptance Criteria

### Feature 1: `gs modify`
- [ ] `gs modify` with staged changes amends to current branch's last commit
- [ ] `gs modify -a` stages all tracked changes before amending
- [ ] `gs modify -c -m "msg"` creates a new commit (does not amend)
- [ ] `gs modify -m "new message"` amends with new commit message
- [ ] `gs modify --into <branch>` amends changes into a specific downstack branch
- [ ] After modify, all upstack branches are automatically rebased
- [ ] Conflicts during auto-restack save progress and allow `--continue`
- [ ] Modify on a frozen branch is blocked with clear error
- [ ] Modify with nothing to commit errors gracefully
- [ ] Original branch is restored after modify + restack completes

### Feature 2: `gs undo`
- [ ] `gs undo` reverts the last mutating operation (state + branch positions)
- [ ] Undo journal is populated by: create, delete, modify, restack, sync, stack delete
- [ ] Journal entries contain: operation, timestamp, pre_state, branch_shas, head info
- [ ] Journal is capped at 10 entries (oldest pruned)
- [ ] `gs undo` with dirty working tree warns and aborts
- [ ] `gs undo` with empty journal shows "Nothing to undo"
- [ ] `gs undo` correctly restores branch SHAs using `git branch -f`
- [ ] `gs undo` returns user to their original branch position
- [ ] Corrupt/missing journal file is handled gracefully
- [ ] After undo, the undo itself is recorded (enabling undo-of-undo)

### Feature 3: Collaboration
- [ ] `gs freeze` marks current branch as frozen in state
- [ ] `gs freeze <name>` marks a specific branch as frozen
- [ ] `gs unfreeze` / `gs unfreeze <name>` removes frozen status
- [ ] Frozen branches are skipped during `gs restack`
- [ ] `gs create` on top of a frozen branch is blocked
- [ ] `gs modify` on a frozen branch is blocked
- [ ] `gs log` displays frozen indicator for frozen branches
- [ ] `gs get <branch>` fetches branch and discovers its stack via PR chain
- [ ] `gs get` creates local branches and registers stack in state
- [ ] `gs get` handles single branches (no PR/stack detected) gracefully

---

## Risks & Considerations

1. **Undo with force-pushed branches:** If user runs `gs undo` after a `gs submit` (which force-pushes), the remote will be ahead of local. Undo only restores local state — it cannot un-push. Document this clearly.

2. **Journal size:** Storing full state snapshots × 10 could grow large for repos with many stacks. In practice, state.json is small (< 50KB even with 50+ branches), so this should be fine.

3. **Concurrent modifications:** If user runs git commands directly (outside gs), the journal's branch_shas may not match reality. Undo should verify SHAs are reachable before resetting.

4. **Frozen branch in middle of stack during restack:** If branch B is frozen in a stack A→B→C→D, restacking should skip B but still rebase C onto B (using B's current HEAD as the new base). This means C's parent reference stays as B.

5. **`gs get` depends on `gh` CLI:** Unlike most commands, `gs get` requires GitHub CLI for stack discovery. Should work without it (single-branch fetch only) with a warning.

6. **Modify with rebase conflicts is complex UX:** User needs to understand that `gs modify --continue` is equivalent to `gs restack --continue`. Clear messaging is critical.

7. **Backward compatibility:** Adding `frozen` field to branch metadata requires `_validate_state()` to default it to `False`. Existing state files will be seamlessly upgraded on next load.

---

## Testing Strategy

### Unit Tests
- `test_journal.py`: Journal I/O, pruning at 10 entries, atomic writes, corrupt file handling
- `test_store.py` additions: Validate `frozen` field defaults, `is_branch_frozen()` helper

### Integration Tests

**`test_modify.py`:**
- Amend with staged changes updates commit
- Amend with `-a` stages all and amends
- New commit with `-c -m` creates commit (not amend)
- Auto-restack after modify succeeds (3-branch stack)
- Conflict during auto-restack saves progress
- `--continue` completes remaining restack
- `--into` modifies specific downstack branch
- Frozen branch blocks modify
- No staged changes errors

**`test_undo.py`:**
- Undo after create restores state and branch positions
- Undo after delete restores deleted branch
- Undo after restack restores original branch positions
- Undo with dirty tree warns and aborts
- Undo with empty journal errors
- Journal caps at 10 entries
- Undo-of-undo works (restore after restore)
- Unreachable SHA handled gracefully

**`test_freeze.py`:**
- Freeze sets frozen=True in state
- Unfreeze sets frozen=False
- Freeze with no args uses current branch
- Restack skips frozen branches
- Create on frozen parent blocked
- Already-frozen shows info (not error)
- Freeze non-stacked branch errors

**`test_get.py` (mocked gh):**
- Single branch fetch (no PR) creates single-branch stack
- Multi-branch stack discovered via PR chain
- Branch already exists locally errors without --force
- Remote branch not found errors clearly

### E2E Tests
- Full modify workflow: create stack → commit → modify middle → verify restack
- Undo workflow: create → modify → undo → verify original state
- Freeze workflow: freeze → attempt modify → unfreeze → modify succeeds

---

## Implementation Order Recommendation

| Phase | Feature | Estimated Effort | Rationale |
|-------|---------|-----------------|-----------|
| 1 | `journal.py` + `gs undo` | 1 day | Foundation for safety; independent of other features |
| 2 | Restack refactor (extract `restack_from`) | 0.5 day | Required before modify; small, well-tested change |
| 3 | `gs freeze` / `gs unfreeze` | 0.5 day | Simple state flag; needed before modify for guard checks |
| 4 | `gs modify` + auto-restack | 1.5 days | Core complexity; depends on phases 1-3 |
| 5 | `gs get` | 1 day | Independent; depends only on `github.py` |
| 6 | Add snapshots to existing commands | 0.5 day | Wire undo into create/delete/restack/sync |
| 7 | Update completions + help text | 0.25 day | Polish |
| 8 | Full test suite | 1.5 days | Parallel with implementation |

**Total estimated effort: ~7 days**

Phases 1-4 should be implemented sequentially. Phases 5-8 can be parallelized.
