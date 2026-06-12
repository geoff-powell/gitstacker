"""gs sync - Fetch latest trunk and restack."""

from ..git_ops import (
    get_current_branch, checkout, fetch_remote, pull_rebase,
)
from ..store import load_state
from ..output import success, error, info
from .restack import cmd_restack


def cmd_sync(args: list[str]) -> None:
    state = load_state()
    current_branch = get_current_branch()

    info("Fetching from remote...")
    fetch_remote()

    # Update trunk
    trunk = state["trunk"]
    info(f"Updating trunk ({trunk})...")
    checkout(trunk)
    result = pull_rebase(trunk)

    if not result.success:
        error(f"Failed to update trunk: {result.stderr}")
        checkout(current_branch)
        raise SystemExit(1)

    success(f"Trunk updated: {trunk}")

    # Return to original branch
    checkout(current_branch)

    # Restack
    print()
    cmd_restack(args)
