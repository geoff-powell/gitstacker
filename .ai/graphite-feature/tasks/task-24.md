# Task 24: Implement `gs get` Collaboration Command

## Description
Create the `gs get <branch>` command that fetches a remote branch and discovers its full stack by walking the PR base chain via `gh pr view`. This enables team collaboration on shared stacks.

## Dependencies
- None (uses existing `github.py` patterns)

## Affected Files
- `gitstacker/commands/get.py` — **new** (command implementation)
- `gitstacker/github.py` — add `get_pr_base_branch()` helper if not present

## Implementation Details

### New file: `gitstacker/commands/get.py`

```python
"""gs get <branch> - Fetch a remote branch and discover its stack."""

import sys
from ..git_ops import (
    get_current_branch, checkout, git, git_or_throw,
    branch_exists, get_commit_hash, fetch_remote,
)
from ..store import (
    load_state, save_state, get_current_stack,
    create_stack, add_branch_to_stack,
)
from ..output import success, error, info, warn, bold, dim


def _get_pr_base(branch: str) -> str | None:
    """Get the base branch of a PR for the given branch via gh CLI.
    
    Returns the base branch name, or None if no PR found.
    """
    import subprocess
    result = subprocess.run(
        ["gh", "pr", "view", branch, "--json", "baseRefName", "-q", ".baseRefName"],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0 and result.stdout.strip():
        return result.stdout.strip()
    return None


def _check_gh_available() -> bool:
    """Check if gh CLI is installed and authenticated."""
    import subprocess
    result = subprocess.run(
        ["gh", "auth", "status"],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def discover_stack_from_prs(branch: str, trunk: str) -> list[str]:
    """Walk PR base chain to discover full stack ordering (bottom-to-top).
    
    Starting from `branch`, follows each PR's base branch until reaching trunk.
    Returns the ordered list of branches forming the stack.
    """
    stack = []
    current = branch
    seen = set()  # Detect circular references
    
    while current and current != trunk:
        if current in seen:
            # Circular reference detected
            break
        seen.add(current)
        stack.append(current)
        
        base = _get_pr_base(current)
        if not base:
            break  # No PR found, stop walking
        current = base
    
    stack.reverse()  # Bottom-to-top order
    return stack


def cmd_get(args: list[str]) -> None:
    """Fetch a remote branch and discover its stack."""
    
    if not args:
        error("Branch name required.")
        info("Usage: gs get <branch>")
        raise SystemExit(1)
    
    branch = args[0]
    force = "--force" in args or "-f" in args
    
    state = load_state()
    trunk = state["trunk"]
    
    # Check if branch already exists locally and is in a stack
    if branch_exists(branch) and not force:
        existing_stack = get_current_stack(state, branch)
        if existing_stack:
            error(f'"{branch}" already exists locally and is in stack "{existing_stack["name"]}".')
            info("Use --force to overwrite, or switch to it with `gs stack switch`.")
            raise SystemExit(1)
    
    # Fetch from remote
    info(f"Fetching from remote...")
    fetch_result = git("fetch", "origin", branch)
    if not fetch_result.success:
        error(f'Branch "{branch}" not found on remote.')
        info(f"Error: {fetch_result.stderr}")
        raise SystemExit(1)
    
    # Try to discover stack via PRs
    has_gh = _check_gh_available()
    stack_branches = []
    
    if has_gh:
        info("Discovering stack via PR chain...")
        stack_branches = discover_stack_from_prs(branch, trunk)
    
    if not stack_branches:
        # Fallback: just use the single branch
        stack_branches = [branch]
        if has_gh:
            info("No PR chain found — fetching as single branch.")
        else:
            warn("GitHub CLI (gh) not available — cannot discover full stack.")
            info("Install gh and run `gh auth login` for full stack discovery.")
            info("Fetching single branch only.")
    
    print()
    info(f"Stack discovered: {' → '.join(bold(b) for b in stack_branches)}")
    print()
    
    # Fetch and create all branches locally
    for b in stack_branches:
        if b == branch:
            # Already fetched above
            pass
        else:
            fetch_b = git("fetch", "origin", b)
            if not fetch_b.success:
                warn(f'Could not fetch "{b}" — skipping.')
                stack_branches = [x for x in stack_branches if x != b]
                continue
        
        if not branch_exists(b):
            # Create local tracking branch
            create_result = git("checkout", "-b", b, f"origin/{b}")
            if create_result.success:
                info(f"  Created: {bold(b)}")
            else:
                warn(f"  Could not create {b}: {create_result.stderr}")
                stack_branches = [x for x in stack_branches if x != b]
        elif force:
            # Reset existing branch to remote
            git("checkout", b)
            git("reset", "--hard", f"origin/{b}")
            info(f"  Reset: {bold(b)} → origin/{b}")
        else:
            info(f"  Exists: {bold(b)} (keeping local version)")
    
    # Register stack in state
    # Generate stack name from the top branch
    stack_name = f"remote-{branch}"
    
    # Check if stack name already exists
    counter = 1
    original_name = stack_name
    while stack_name in state["stacks"]:
        if force:
            # Remove existing stack registration (not git branches)
            for b in state["stacks"][stack_name].get("branches", []):
                state["branches"].pop(b, None)
            del state["stacks"][stack_name]
            break
        stack_name = f"{original_name}-{counter}"
        counter += 1
    
    # Create the stack
    create_stack(state, stack_name, trunk)
    
    # Add branches to stack
    for i, b in enumerate(stack_branches):
        parent = trunk if i == 0 else stack_branches[i - 1]
        
        if b not in state["branches"]:
            add_branch_to_stack(state, stack_name, b, parent)
            try:
                state["branches"][b]["commit_base"] = get_commit_hash(parent)
            except RuntimeError:
                state["branches"][b]["commit_base"] = None
        else:
            # Branch metadata already exists (maybe from force overwrite)
            if b not in state["stacks"][stack_name]["branches"]:
                state["stacks"][stack_name]["branches"].append(b)
    
    save_state(state)
    
    # Checkout the requested branch
    try:
        checkout(branch)
    except RuntimeError:
        pass
    
    print()
    success(f'Got stack "{bold(stack_name)}" ({len(stack_branches)} branches)')
    info(f"Now on: {bold(branch)}")
```

### Helper addition to `gitstacker/github.py` (if needed)

Check if `github.py` already has a function to get PR info for a branch. If not, the `_get_pr_base()` function in `get.py` handles it inline using subprocess directly (consistent with the pattern in `github.py` which also calls `gh` via subprocess).

## Acceptance Criteria
- [ ] `gs get <branch>` fetches the branch from remote
- [ ] When `gh` is available, discovers the full stack by walking PR base chain
- [ ] Creates local branches for all discovered stack members
- [ ] Registers the discovered stack in state.json with correct parent relationships
- [ ] Names the stack `remote-<branch>` (with counter suffix if name exists)
- [ ] `gs get` with no args shows usage error
- [ ] `gs get <branch>` when branch exists locally + is in stack errors without `--force`
- [ ] `gs get <branch> --force` overwrites existing local branches
- [ ] When `gh` is not available, falls back to single-branch fetch with warning
- [ ] When no PR chain is found, creates single-branch stack
- [ ] Circular PR base references are detected and handled (stops walking)
- [ ] Remote branch not found shows clear error
- [ ] After successful get, user is on the requested branch
