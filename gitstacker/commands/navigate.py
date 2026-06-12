"""gs up/down/top/bottom - Navigate branches within a stack."""

from ..git_ops import get_current_branch, checkout
from ..store import load_state, get_current_stack, get_branch_position
from ..output import success, error, warn


def cmd_navigate(direction: str, args: list[str]) -> None:
    state = load_state()
    current_branch = get_current_branch()
    stack = get_current_stack(state, current_branch)

    if not stack:
        # If on trunk with a current stack, jump into it
        if current_branch == state["trunk"] and state.get("current_stack"):
            target_stack = state["stacks"].get(state["current_stack"])
            if target_stack and target_stack["branches"]:
                if direction in ("bottom", "down"):
                    target = target_stack["branches"][0]
                else:
                    target = target_stack["branches"][-1]
                checkout(target)
                success(f"Moved to: {target}")
                return

        error("Not on a stacked branch. Use `gs stack switch <name>` first.")
        raise SystemExit(1)

    pos = get_branch_position(stack, current_branch)
    count = int(args[0]) if args else 1

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
