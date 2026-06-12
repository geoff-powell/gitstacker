"""gs stack - Stack management commands."""

from ..git_ops import get_current_branch, checkout
from ..store import (
    load_state, save_state, create_stack,
    get_current_stack, delete_stack,
)
from ..output import (
    success, error, info, heading,
    bold, cyan, green, dim, gray, symbols,
)


def cmd_stack(args: list[str]) -> None:
    if not args:
        return stack_list()

    sub = args[0]
    sub_args = args[1:]

    if sub in ("new", "create"):
        return stack_new(sub_args)
    elif sub in ("list", "ls"):
        return stack_list()
    elif sub in ("switch", "sw"):
        return stack_switch(sub_args)
    elif sub in ("delete", "rm"):
        return stack_delete(sub_args)
    else:
        # Treat as `gs stack new <name>`
        return stack_new(args)


def stack_new(args: list[str]) -> None:
    if not args:
        error("Stack name required. Usage: gs stack new <name>")
        raise SystemExit(1)

    name = args[0]
    state = load_state()

    try:
        create_stack(state, name, state["trunk"])
        state["current_stack"] = name
        save_state(state)
        success(f'Created stack "{name}" (base: {state["trunk"]})')
        info("Create branches with: gs create <branch-name>")
    except RuntimeError as e:
        error(str(e))
        raise SystemExit(1)


def stack_list() -> None:
    state = load_state()
    current_branch = get_current_branch()
    stacks = state["stacks"]

    if not stacks:
        info("No stacks yet. Create one with: gs stack new <name>")
        return

    heading("Stacks")
    print()

    for s in stacks.values():
        active_stack = get_current_stack(state, current_branch)
        is_active = active_stack is not None and active_stack["name"] == s["name"]
        marker = green(" (active)") if is_active else ""
        count = len(s["branches"])
        plural = "es" if count != 1 else ""
        trunk_name = s["trunk"]

        ptr = symbols.pointer if is_active else " "
        print(f"  {ptr} {bold(s['name'])}{marker} {dim(f'[{count} branch{plural}]')} {gray(f'base: {trunk_name}')}")

        for i, branch in enumerate(s["branches"]):
            is_last = i == len(s["branches"]) - 1
            is_curr = branch == current_branch
            prefix = symbols.corner if is_last else symbols.branch
            branch_display = cyan(branch) if is_curr else branch
            pr_num = state["branches"].get(branch, {}).get("pr_number")
            pr_info = dim(f" #{pr_num}") if pr_num else ""
            print(f"      {prefix}{symbols.line} {branch_display}{pr_info}")

        print()


def stack_switch(args: list[str]) -> None:
    if not args:
        error("Stack name required. Usage: gs stack switch <name>")
        raise SystemExit(1)

    name = args[0]
    state = load_state()
    target = state["stacks"].get(name)

    if not target:
        error(f'Stack "{name}" not found.')
        available = list(state["stacks"].keys())
        if available:
            info(f"Available stacks: {', '.join(available)}")
        raise SystemExit(1)

    state["current_stack"] = name
    save_state(state)

    if target["branches"]:
        top_branch = target["branches"][-1]
        checkout(top_branch)
        success(f'Switched to stack "{name}" (branch: {top_branch})')
    else:
        success(f'Switched to stack "{name}" (no branches yet)')


def stack_delete(args: list[str]) -> None:
    if not args:
        error("Stack name required. Usage: gs stack delete <name>")
        raise SystemExit(1)

    name = args[0]
    state = load_state()

    try:
        stack = state["stacks"].get(name)
        if not stack:
            raise RuntimeError(f'Stack "{name}" not found')

        branch_count = len(stack["branches"])
        delete_stack(state, name)
        save_state(state)
        success(f'Deleted stack "{name}"')
        if branch_count > 0:
            info("Note: Git branches still exist. Delete them manually if needed.")
    except RuntimeError as e:
        error(str(e))
        raise SystemExit(1)
