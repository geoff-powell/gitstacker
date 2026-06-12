"""gs trunk - Show or set the trunk branch."""

from ..git_ops import branch_exists
from ..store import load_state, save_state
from ..output import success, error, info, warn


def cmd_trunk(args: list[str]) -> None:
    state = load_state()

    if not args:
        info(f"Trunk branch: {state['trunk']}")
        return

    new_trunk = args[0]

    if not branch_exists(new_trunk):
        error(f'Branch "{new_trunk}" does not exist.')
        raise SystemExit(1)

    old_trunk = state["trunk"]
    state["trunk"] = new_trunk

    # Update stacks that referenced the old trunk
    affected = [s["name"] for s in state["stacks"].values() if s["trunk"] == old_trunk]
    if affected:
        for name in affected:
            state["stacks"][name]["trunk"] = new_trunk
        warn(f"Updated {len(affected)} stack(s) to use new trunk: {', '.join(affected)}")

    save_state(state)
    success(f"Trunk branch set to: {new_trunk}")
