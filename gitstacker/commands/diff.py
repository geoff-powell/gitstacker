"""gs diff - Show diff of current branch vs its parent in the stack."""

import subprocess
import sys
from ..git_ops import get_current_branch, get_merge_base
from ..store import load_state, get_current_stack, get_parent_branch
from ..output import error, info
from ..prompts import offer_track_current_branch


def cmd_diff(args: list[str]) -> None:
    """Show diff between current branch and its stack parent.

    This shows what THIS branch adds, not what HEAD~1 adds.
    Uses merge-base to find the fork point, then diffs from there to HEAD.
    """
    state = load_state()
    current_branch = get_current_branch()

    # Find the stack and parent
    stack = get_current_stack(state, current_branch)
    if not stack:
        stack = offer_track_current_branch(state, current_branch)

    parent = get_parent_branch(state, stack, current_branch)

    # Get the merge base (fork point)
    merge_base = get_merge_base(parent, current_branch)

    # Build diff command
    diff_args = ["git", "diff"]

    # Pass through any extra args (e.g., --stat, --name-only, file paths)
    remaining_args = []
    for a in args:
        if a in ("--stat", "--name-only", "--cached", "--no-color"):
            diff_args.append(a)
        else:
            remaining_args.append(a)

    diff_args.append(f"{merge_base}..HEAD")

    # Add any remaining args (file paths)
    diff_args.extend(remaining_args)

    # Run diff with output going directly to terminal (for pager support)
    result = subprocess.run(diff_args)
    sys.exit(result.returncode)
