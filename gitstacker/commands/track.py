"""gs track [branch] - Track an existing branch into the current stack."""

import sys
from typing import Optional

from ..git_ops import (
    get_current_branch,
    branch_exists,
    get_commit_hash,
    get_merge_base,
    get_commit_count,
    is_ancestor,
    list_branches,
    is_working_tree_clean,
)
from ..store import (
    load_state,
    save_state,
    get_current_stack,
    get_branch_position,
)
from ..output import success, error, info, warn, bold, dim, cyan
from ..journal import snapshot_before


def detect_parent(
    target: str,
    trunk: str,
    all_branches: list[str],
) -> str | list[str]:
    """Detect the parent branch for target.

    Returns a single branch name if unambiguous, or a list of candidates
    if multiple branches are at the same distance (caller should prompt).
    """
    candidates: list[tuple[str, int]] = []

    for branch in all_branches:
        if branch == target:
            continue

        # Check if branch is a direct ancestor of target
        if not is_ancestor(branch, target):
            continue

        # Compute distance (commits between branch tip and target tip)
        distance = get_commit_count(branch, target)
        candidates.append((branch, distance))

    if not candidates:
        return trunk

    # Sort by distance (closest first)
    candidates.sort(key=lambda x: x[1])
    closest_distance = candidates[0][1]

    # Get all branches at the same closest distance
    closest = [b for b, d in candidates if d == closest_distance]

    if len(closest) == 1:
        return closest[0]
    else:
        return closest  # Ambiguous — caller should prompt


def prompt_choose_parent(candidates: list[str], target: str) -> str:
    """Interactive prompt for user to choose among ambiguous parent candidates."""
    print()
    print(f"Multiple branches could be the parent of {bold(target)}:")
    print()
    for i, branch in enumerate(candidates, 1):
        print(f"  {cyan(str(i))}. {branch}")
    print()

    while True:
        try:
            choice = input(f"Which branch is the parent? [1-{len(candidates)}]: ").strip()
            idx = int(choice) - 1
            if 0 <= idx < len(candidates):
                return candidates[idx]
            print(f"  Please enter a number between 1 and {len(candidates)}")
        except (ValueError, EOFError):
            print(f"  Please enter a number between 1 and {len(candidates)}")
        except KeyboardInterrupt:
            print()
            raise SystemExit(1)


def insert_branch_in_stack(state: dict, stack: dict, branch_name: str, parent: str) -> None:
    """Insert a branch into the stack at the correct position (after parent).

    If parent is trunk, inserts at the beginning.
    If parent is in the stack, inserts right after it.
    """
    if parent == stack["trunk"] or parent not in stack["branches"]:
        # Find the right position: after any existing branches that are
        # ancestors of our branch, or at the end
        pos = 0
        for i, existing in enumerate(stack["branches"]):
            if is_ancestor(existing, branch_name):
                pos = i + 1
        stack["branches"].insert(pos, branch_name)
    else:
        parent_pos = get_branch_position(stack, parent)
        stack["branches"].insert(parent_pos + 1, branch_name)

    state["branches"][branch_name] = {
        "name": branch_name,
        "parent": parent,
        "pr_number": None,
        "pr_url": None,
        "commit_base": None,
        "frozen": False,
    }


def track_branch(
    target: str,
    state: dict,
    stack: Optional[dict] = None,
    _depth: int = 0,
) -> bool:
    """Track a branch into a stack, handling walk-up recursion.

    Returns True if successfully tracked, False otherwise.
    """
    if _depth > 20:
        error("Too many levels of untracked parents. Aborting.")
        return False

    # Validate branch exists
    if not branch_exists(target):
        error(f'Branch "{target}" does not exist.')
        return False

    # Check if already tracked
    existing_stack = get_current_stack(state, target)
    if existing_stack:
        if _depth == 0:
            error(f'Branch "{target}" is already tracked in stack "{existing_stack["name"]}".')
        return True  # Already tracked is fine for recursive calls

    # Determine stack
    if not stack:
        if state.get("current_stack"):
            stack = state["stacks"].get(state["current_stack"])
        if not stack:
            error("No active stack. Create one first with: gs stack new <name>")
            return False

    trunk = stack["trunk"]

    # Don't track trunk itself
    if target == trunk:
        error(f'Cannot track trunk branch "{trunk}".')
        return False

    # Detect parent
    all_branches = list_branches()
    parent_result = detect_parent(target, trunk, all_branches)

    if isinstance(parent_result, list):
        # Ambiguous — prompt user
        parent = prompt_choose_parent(parent_result, target)
    else:
        parent = parent_result

    # Check if parent is frozen
    if parent in state["branches"] and state["branches"][parent].get("frozen", False):
        error(f'Cannot track on top of frozen branch "{parent}".')
        info(f"Unfreeze it first: gs unfreeze {parent}")
        return False

    # Walk-up: if parent is not trunk and not tracked, offer to track it
    if parent != trunk and not get_current_stack(state, parent):
        indent = "  " * _depth
        print(f'{indent}Parent branch {bold(parent)} is not tracked.')
        try:
            response = input(f"{indent}Track it first? [Y/n]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            return False

        if response in ("", "y", "yes"):
            if not track_branch(parent, state, stack, _depth + 1):
                return False
        else:
            # User declined — use trunk as parent instead
            info(f"Using {trunk} as parent instead.")
            parent = trunk

    # Compute commit_base
    try:
        commit_base = get_merge_base(parent, target)
    except RuntimeError:
        commit_base = get_commit_hash(parent)

    # Insert into stack
    indent = "  " * _depth
    insert_branch_in_stack(state, stack, target, parent)
    state["branches"][target]["commit_base"] = commit_base

    prefix = dim("tracked") if _depth > 0 else ""
    if _depth > 0:
        print(f"{indent}{dim('tracked')} {target} (parent: {parent})")

    return True


def cmd_track(args: list[str]) -> None:
    """Track an existing branch into the current stack."""
    # Determine target branch
    if args and not args[0].startswith("-"):
        target = args[0]
    else:
        target = get_current_branch()

    if not branch_exists(target):
        error(f'Branch "{target}" does not exist.')
        raise SystemExit(1)

    state = load_state()
    snapshot_before("track", state)

    # Check if already tracked
    existing_stack = get_current_stack(state, target)
    if existing_stack:
        error(f'Branch "{target}" is already tracked in stack "{existing_stack["name"]}".')
        raise SystemExit(1)

    # Find active stack
    stack = None
    if state.get("current_stack"):
        stack = state["stacks"].get(state["current_stack"])

    if not stack:
        error("No active stack. Create one first with: gs stack new <name>")
        raise SystemExit(1)

    # Track the branch (with walk-up if needed)
    result = track_branch(target, state, stack)

    if result:
        state["current_stack"] = stack["name"]
        save_state(state)

        parent = state["branches"][target]["parent"]
        success(f'Tracked "{target}" on stack "{stack["name"]}"')
        info(f"Parent: {parent}")
    else:
        raise SystemExit(1)
