"""gs create <name> - Create a new branch and add it to the current stack."""

from ..git_ops import (
    get_current_branch, create_branch, branch_exists,
    get_commit_hash, checkout, is_working_tree_clean,
)
from ..store import (
    load_state, save_state, get_current_stack, add_branch_to_stack,
)
from ..output import success, error, info
from ..journal import snapshot_before


def cmd_create(args: list[str]) -> None:
    if not args:
        error("Branch name required. Usage: gs create <branch-name>")
        raise SystemExit(1)

    if not is_working_tree_clean():
        error("Working tree has uncommitted changes.")
        info("Commit or stash your changes before creating a new branch.")
        raise SystemExit(1)

    name = args[0]

    if branch_exists(name):
        error(f'Branch "{name}" already exists.')
        raise SystemExit(1)

    state = load_state()
    snapshot_before("create", state)
    current_branch = get_current_branch()

    # Check if current branch (the parent) is frozen
    if current_branch in state["branches"] and state["branches"][current_branch].get("frozen", False):
        error(f'Cannot create on top of frozen branch "{current_branch}".')
        info(f'Unfreeze it first: gs unfreeze {current_branch}')
        raise SystemExit(1)

    # Determine which stack to add to
    stack = get_current_stack(state, current_branch)

    # If not on a stacked branch, try current_stack
    if not stack and state.get("current_stack"):
        stack = state["stacks"].get(state["current_stack"])

    if not stack:
        error("No active stack. Create one first with: gs stack new <name>")
        raise SystemExit(1)

    # Parent is the current branch (if in stack) or the top of stack or trunk
    if current_branch in stack["branches"]:
        parent = current_branch
    elif stack["branches"]:
        parent = stack["branches"][-1]
    else:
        parent = stack["trunk"]

    # Switch to parent if not already there
    if current_branch != parent:
        checkout(parent)

    # Create the branch
    create_branch(name)

    # Store commit base for restacking
    commit_base = get_commit_hash("HEAD")

    # Add to stack
    add_branch_to_stack(state, stack["name"], name, parent)
    state["branches"][name]["commit_base"] = commit_base
    state["current_stack"] = stack["name"]
    save_state(state)

    success(f'Created branch "{name}" on stack "{stack["name"]}"')
    info(f"Parent: {parent}")
