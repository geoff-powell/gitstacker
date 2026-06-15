# Task 23: Implement `gs modify` Command with Auto-Restack

## Description
Create the `gs modify` command that amends or commits changes to a branch and automatically restacks all upstack branches. This is the core productivity feature — it mirrors Graphite's `gt modify` behavior.

## Dependencies
- Task 18 (journal.py for snapshot_before)
- Task 21 (restack_from() extracted function)
- Task 22 (frozen branch checks)

## Affected Files
- `gitstacker/commands/modify.py` — **new** (full command implementation)

## Implementation Details

### New file: `gitstacker/commands/modify.py`

```python
"""gs modify - Amend/commit to a branch and auto-restack upstack branches."""

import sys
from ..git_ops import (
    get_current_branch, checkout, get_commit_hash,
    is_working_tree_clean, git,
)
from ..store import (
    load_state, save_state, get_current_stack, get_parent_branch,
    get_branch_position,
)
from ..journal import snapshot_before
from ..output import success, error, info, warn, bold, dim
from .restack import restack_from


def _extract_flag_value(args: list[str], long_flag: str, short_flag: str = "") -> tuple[str, list[str]]:
    """Extract a flag value from args. Returns (value, remaining_args).
    
    For --message "foo" or -m "foo", returns ("foo", args_without_flag_and_value).
    Returns ("", original_args) if flag not found.
    """
    remaining = []
    value = ""
    i = 0
    while i < len(args):
        if args[i] in (long_flag, short_flag) and short_flag:
            if i + 1 < len(args):
                value = args[i + 1]
                i += 2
                continue
        elif args[i] == long_flag:
            if i + 1 < len(args):
                value = args[i + 1]
                i += 2
                continue
        # Handle --flag=value form
        elif args[i].startswith(f"{long_flag}="):
            value = args[i][len(long_flag) + 1:]
            i += 1
            continue
        remaining.append(args[i])
        i += 1
    return value, remaining


def cmd_modify(args: list[str]) -> None:
    """Amend or commit to a branch, then auto-restack everything above."""
    
    # Handle --continue (delegates to restack --continue)
    if "--continue" in args:
        from .restack import cmd_restack
        return cmd_restack(["--continue"])
    
    # Parse flags
    is_new_commit = "--commit" in args or "-c" in args
    stage_all = "--all" in args or "-a" in args
    
    # Remove boolean flags from args for value extraction
    clean_args = [a for a in args if a not in ("--commit", "-c", "--all", "-a")]
    
    # Extract --message / -m value
    message, clean_args = _extract_flag_value(clean_args, "--message", "-m")
    
    # Extract --into value
    target_branch, clean_args = _extract_flag_value(clean_args, "--into")
    
    # Load state
    state = load_state()
    current_branch = get_current_branch()
    
    # Determine which branch to modify
    branch_to_modify = target_branch or current_branch
    
    # Validate: branch must be in a stack
    stack = get_current_stack(state, branch_to_modify)
    if not stack:
        error(f'"{branch_to_modify}" is not in any stack.')
        info("Use `gs create` to add branches to a stack first.")
        raise SystemExit(1)
    
    # Validate: branch must not be frozen
    meta = state["branches"].get(branch_to_modify, {})
    if meta.get("frozen", False):
        error(f'Branch "{branch_to_modify}" is frozen.')
        info(f"Unfreeze it first: gs unfreeze {branch_to_modify}")
        raise SystemExit(1)
    
    # Validate: for new commit, message is required
    if is_new_commit and not message:
        error("--message / -m is required when using --commit / -c.")
        info("Usage: gs modify -c -m \"commit message\"")
        raise SystemExit(1)
    
    # Snapshot for undo
    snapshot_before("modify", state)
    
    # If targeting a different branch, switch to it
    switched = False
    if target_branch and target_branch != current_branch:
        info(f"Switching to {bold(target_branch)}...")
        checkout(target_branch)
        switched = True
    
    # Stage changes
    if stage_all:
        stage_result = git("add", "-A")
        if not stage_result.success:
            error(f"Failed to stage changes: {stage_result.stderr}")
            if switched:
                checkout(current_branch)
            raise SystemExit(1)
    
    # Check there's something to commit/amend
    status_result = git("status", "--porcelain")
    has_staged = any(line[0] != ' ' and line[0] != '?' for line in status_result.stdout.split('\n') if line)
    
    if not is_new_commit and not stage_all and not has_staged:
        # For amend without -a, check if there are staged changes
        error("No changes staged for amend.")
        info("Stage changes manually, or use -a to stage all tracked changes.")
        if switched:
            checkout(current_branch)
        raise SystemExit(1)
    
    # Perform the commit/amend
    if is_new_commit:
        # New commit
        commit_args = ["commit", "-m", message]
        if stage_all:
            commit_args = ["commit", "-a", "-m", message]
        result = git(*commit_args)
    else:
        # Amend
        if message:
            commit_args = ["commit", "--amend", "-m", message]
        else:
            commit_args = ["commit", "--amend", "--no-edit"]
        if stage_all and not has_staged:
            # If -a was used but nothing was explicitly staged, add -a to commit
            commit_args.insert(1, "-a")
        result = git(*commit_args)
    
    if not result.success:
        error(f"Commit failed: {result.stderr}")
        if switched:
            checkout(current_branch)
        raise SystemExit(1)
    
    action = "Committed" if is_new_commit else "Amended"
    success(f"{action}: {bold(branch_to_modify)}")
    
    # Update commit_base for the modified branch
    parent = get_parent_branch(state, stack, branch_to_modify)
    state["branches"][branch_to_modify]["commit_base"] = get_commit_hash(parent)
    
    # Restack everything above the modified branch
    branch_pos = get_branch_position(stack, branch_to_modify)
    branches_above = len(stack["branches"]) - branch_pos - 1
    
    if branches_above > 0:
        print()
        info(f"Restacking {branches_above} branch(es) above {bold(branch_to_modify)}...")
        print()
        
        all_ok, failed_branch, rebased = restack_from(
            state, stack, start_index=branch_pos + 1, skip_frozen=True
        )
        
        if not all_ok:
            # Save progress for --continue
            state["_restack_progress"] = {
                "stack": stack["name"],
                "failed_at": failed_branch,
                "completed": rebased,
                "original_branch": current_branch,
            }
            save_state(state)
            print()
            warn(f'Auto-restack stopped at "{failed_branch}" due to conflicts.')
            info("Resolve conflicts, then run `gs modify --continue`.")
            return
        else:
            state.pop("_restack_progress", None)
    
    # Save final state
    save_state(state)
    
    # Return to original branch if we switched
    if switched:
        checkout(current_branch)
        info(f"Returned to: {bold(current_branch)}")
    
    if branches_above > 0:
        print()
        success("Modified and restacked successfully!")
    else:
        print()
        success("Modified successfully! (no upstack branches to restack)")
```

### Command flags summary:

| Flag | Short | Behavior |
|------|-------|----------|
| (none) | | Amend staged changes to current branch, keep message |
| `--all` | `-a` | Stage all tracked changes before amend/commit |
| `--commit` | `-c` | Create new commit instead of amending |
| `--message "msg"` | `-m "msg"` | Set commit message (required with -c) |
| `--into <branch>` | | Target a specific downstack branch |
| `--continue` | | Resume after restack conflict (delegates to restack) |

### Interaction examples:
```bash
# Amend staged changes to current branch
gs modify

# Stage all + amend with new message  
gs modify -a -m "better message"

# New commit on current branch + restack above
gs modify -c -m "add error handling"

# Amend into a specific downstack branch
gs modify -a --into auth-api
```

## Acceptance Criteria
- [ ] `gs modify` with staged changes amends the current branch's last commit
- [ ] `gs modify -a` stages all tracked changes before amending
- [ ] `gs modify -c -m "msg"` creates a new commit (not amend)
- [ ] `gs modify -m "msg"` amends with a new commit message
- [ ] `gs modify --into <branch>` modifies a specific downstack branch
- [ ] After modify, all upstack branches are automatically restacked
- [ ] Frozen branches are skipped during auto-restack
- [ ] Conflicts during auto-restack save progress and allow `--continue`
- [ ] `--continue` delegates to `gs restack --continue`
- [ ] Modifying a frozen branch is blocked with clear error
- [ ] Missing `-m` with `-c` shows clear error
- [ ] No staged changes (without `-a`) shows clear error
- [ ] Original branch is restored after `--into` + restack completes
- [ ] Journal snapshot is recorded before any mutations
