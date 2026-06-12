"""gs delete - Remove a branch from its stack."""

from ..git_ops import get_current_branch, checkout, git
from ..store import (
    load_state, save_state, get_current_stack,
    get_parent_branch, remove_branch_from_stack,
)
from ..output import success, error, info, warn


def cmd_delete(args: list[str]) -> None:
    state = load_state()
    force = "--force" in args or "-f" in args

    # Get target branch
    branch = None
    for a in args:
        if not a.startswith("-"):
            branch = a
            break
    if not branch:
        branch = get_current_branch()

    stack = get_current_stack(state, branch)
    if not stack:
        error(f'Branch "{branch}" is not part of any stack.')
        raise SystemExit(1)

    parent = get_parent_branch(state, stack, branch)
    current_branch = get_current_branch()

    # Move to parent if deleting current branch
    if current_branch == branch:
        checkout(parent)

    # Remove from stack
    remove_branch_from_stack(state, branch)
    save_state(state)

    # Optionally delete git branch
    if force:
        result = git("branch", "-D", branch)
        if result.success:
            success(f'Deleted branch "{branch}" from stack and git.')
        else:
            warn(f"Removed from stack but failed to delete git branch: {result.stderr}")
    else:
        success(f'Removed "{branch}" from stack "{stack["name"]}".')
        info("Git branch still exists. Use --force to also delete the git branch.")

    info(f"Moved to: {parent}")
