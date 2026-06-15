"""gs sync - Fetch latest trunk and restack."""

from ..git_ops import (
    get_current_branch, checkout, fetch_remote, pull_rebase,
    is_working_tree_clean,
)
from ..store import load_state
from ..output import success, error, info
from ..journal import snapshot_before
from .restack import cmd_restack


def cmd_sync(args: list[str]) -> None:
    if not is_working_tree_clean():
        error("Working tree has uncommitted changes.")
        info("Commit or stash your changes before syncing.")
        raise SystemExit(1)

    state = load_state()
    snapshot_before("sync", state)
    current_branch = get_current_branch()

    info("Fetching from remote...")
    fetch_remote()

    # Update trunk
    trunk = state["trunk"]
    info(f"Updating trunk ({trunk})...")

    # Only checkout trunk if we're not already on it
    if current_branch != trunk:
        checkout(trunk)

    result = pull_rebase(trunk)

    if not result.success:
        error(f"Failed to update trunk: {result.stderr}")
        if current_branch != trunk:
            checkout(current_branch)
        raise SystemExit(1)

    success(f"Trunk updated: {trunk}")

    # Return to original branch (only if we moved)
    if current_branch != trunk:
        checkout(current_branch)

    # Restack
    print()
    cmd_restack(args)
