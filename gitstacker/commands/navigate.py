"""gs up/down/top/bottom - Navigate branches within a stack."""

from ..git_ops import get_current_branch, checkout, is_working_tree_clean
from ..store import load_state, get_current_stack, get_branch_position
from ..output import success, error, warn, info


def cmd_navigate(direction: str, args: list[str]) -> None:
    if not is_working_tree_clean():
        error("Working tree has uncommitted changes.")
        info("Commit or stash your changes before navigating.")
        raise SystemExit(1)

    state = load_state()
    current_branch = get_current_branch()
    stack = get_current_stack(state, current_branch)

    if not stack:
        # If on trunk with a current stack, jump into it
        if current_branch == state["trunk"] and state.get("current_stack"):
            target_stack = state["stacks"].get(state["current_stack"])
            if target_stack and target_stack["branches"]:
                if direction in ("up", "bottom"):
                    target = target_stack["branches"][0]
                elif direction == "top":
                    target = target_stack["branches"][-1]
                elif direction == "down":
                    warn("Already at the bottom (trunk).")
                    return
                else:
                    target = target_stack["branches"][0]
                checkout(target)
                success(f"Moved to: {target}")
                return

        error("Not on a stacked branch. Use `gs stack switch <name>` first.")
        raise SystemExit(1)

    pos = get_branch_position(stack, current_branch)

    if args:
        try:
            count = int(args[0])
        except ValueError:
            error(f'Invalid count: "{args[0]}". Expected a number.')
            raise SystemExit(1)
        if count < 1:
            error("Count must be at least 1.")
            raise SystemExit(1)
    else:
        count = 1

    if direction == "up":
        target_pos = min(pos + count, len(stack["branches"]) - 1)
    elif direction == "down":
        target_pos = max(pos - count, 0)
    elif direction == "top":
        target_pos = len(stack["branches"]) - 1
    elif direction == "bottom":
        target_pos = 0
    else:
        target_pos = pos

    if target_pos == pos:
        edge = "top" if direction in ("up", "top") else "bottom"
        warn(f"Already at the {edge} of the stack.")
        return

    target_branch = stack["branches"][target_pos]
    checkout(target_branch)
    success(f"Moved to: {target_branch} [{target_pos + 1}/{len(stack['branches'])}]")
