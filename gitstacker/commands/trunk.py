"""gs trunk - Show or set the trunk branch."""

from ..git_ops import branch_exists
from ..store import load_state, save_state
from ..output import success, error, info


def cmd_trunk(args: list[str]) -> None:
    state = load_state()

    if not args:
        info(f"Trunk branch: {state['trunk']}")
        return

    new_trunk = args[0]

    if not branch_exists(new_trunk):
        error(f'Branch "{new_trunk}" does not exist.')
        raise SystemExit(1)

    state["trunk"] = new_trunk
    save_state(state)
    success(f"Trunk branch set to: {new_trunk}")
