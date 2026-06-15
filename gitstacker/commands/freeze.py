"""gs freeze / gs unfreeze - Mark branches as frozen to prevent modifications."""

from ..store import load_state, save_state, get_current_stack
from ..git_ops import get_current_branch
from ..output import success, error, info, bold


def cmd_freeze(args: list[str]) -> None:
    """Freeze a branch to prevent modifications and skip during restack."""
    state = load_state()

    # Determine target branch
    branch = args[0] if args else get_current_branch()

    # Validate branch is tracked
    if branch not in state["branches"]:
        error(f'"{branch}" is not a stacked branch.')
        info("Only branches managed by GitStacker can be frozen.")
        raise SystemExit(1)

    # Check if already frozen
    if state["branches"][branch].get("frozen", False):
        info(f'"{bold(branch)}" is already frozen.')
        return

    # Freeze it
    state["branches"][branch]["frozen"] = True
    save_state(state)
    success(f'Froze "{bold(branch)}" \u2014 it will be skipped during restack and cannot be modified.')


def cmd_unfreeze(args: list[str]) -> None:
    """Unfreeze a branch to allow modifications and restacking."""
    state = load_state()

    # Determine target branch
    branch = args[0] if args else get_current_branch()

    # Validate branch is tracked
    if branch not in state["branches"]:
        error(f'"{branch}" is not a stacked branch.')
        info("Only branches managed by GitStacker can be unfrozen.")
        raise SystemExit(1)

    # Check if not frozen
    if not state["branches"][branch].get("frozen", False):
        info(f'"{bold(branch)}" is not frozen.')
        return

    # Unfreeze it
    state["branches"][branch]["frozen"] = False
    save_state(state)
    success(f'Unfroze "{bold(branch)}" \u2014 it will now be included in restack and can be modified.')
