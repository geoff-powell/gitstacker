"""gs status - Machine-readable status output (JSON) for AI agent consumption."""

import json
from ..git_ops import get_current_branch
from ..store import load_state, get_current_stack, get_parent_branch, is_initialized
from ..output import info


def cmd_status(args: list[str]) -> None:
    """Output current state as JSON (for AI agents) or human-readable."""

    if not is_initialized():
        if "--json" in args:
            print(json.dumps({"initialized": False}))
        else:
            info("GitStacker not initialized. Run `gs init` first.")
        return

    state = load_state()
    current_branch = get_current_branch()
    current_stack = get_current_stack(state, current_branch)

    status = {
        "initialized": True,
        "trunk": state["trunk"],
        "current_branch": current_branch,
        "current_stack": current_stack["name"] if current_stack else None,
        "stack_position": None,
        "stack_size": None,
        "stacks": {},
    }

    if current_stack:
        branches = current_stack["branches"]
        pos = branches.index(current_branch) if current_branch in branches else None
        status["stack_position"] = pos + 1 if pos is not None else None
        status["stack_size"] = len(branches)

    for name, stack in state["stacks"].items():
        status["stacks"][name] = {
            "trunk": stack["trunk"],
            "branches": stack["branches"],
            "branch_count": len(stack["branches"]),
        }
        # Add PR info
        for branch in stack["branches"]:
            meta = state["branches"].get(branch, {})
            if meta.get("pr_number"):
                if "prs" not in status["stacks"][name]:
                    status["stacks"][name]["prs"] = {}
                status["stacks"][name]["prs"][branch] = {
                    "number": meta["pr_number"],
                    "url": meta.get("pr_url"),
                }

    if "--json" in args:
        print(json.dumps(status, indent=2))
    else:
        info(f"Trunk: {state['trunk']}")
        info(f"Branch: {current_branch}")
        if current_stack:
            branches = current_stack["branches"]
            pos = branches.index(current_branch) if current_branch in branches else None
            pos_display = f"{pos + 1}/{len(branches)}" if pos is not None else "N/A"
            info(f"Stack: {current_stack['name']} (position {pos_display})")
        else:
            info("Stack: (not on a stack)")
        stack_count = len(state["stacks"])
        info(f"Total stacks: {stack_count}")
