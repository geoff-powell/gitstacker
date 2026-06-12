"""gs log - Visual display of the current stack."""

from ..git_ops import get_current_branch, get_commit_count, get_short_hash
from ..store import load_state, get_current_stack, get_parent_branch
from ..output import (
    info, heading, bold, cyan, green, yellow, dim, gray, symbols,
)


def cmd_log(args: list[str]) -> None:
    state = load_state()
    current_branch = get_current_branch()

    if "--all" in args or "-a" in args:
        return log_all(state, current_branch)

    # Find current stack
    stack = get_current_stack(state, current_branch)
    if not stack and state.get("current_stack"):
        stack = state["stacks"].get(state["current_stack"])

    if not stack:
        info("Not on a stack. Use `gs log --all` to see all stacks.")
        return

    heading(f"Stack: {stack['name']}")
    trunk_name = stack["trunk"]
    print(f"  {dim(f'base: {trunk_name}')}")
    print()

    # Display from top to bottom
    for i in range(len(stack["branches"]) - 1, -1, -1):
        branch = stack["branches"][i]
        is_current = branch == current_branch
        parent = get_parent_branch(state, stack, branch)
        meta = state["branches"].get(branch, {})

        commit_count = 0
        try:
            commit_count = get_commit_count(parent, branch)
        except Exception:
            pass

        hash_str = ""
        try:
            hash_str = get_short_hash(branch)
        except Exception:
            pass

        pr_num = meta.get("pr_number")
        pr_tag = yellow(f" PR #{pr_num}") if pr_num else ""
        plural = "s" if commit_count > 1 else ""
        commits = dim(f" ({commit_count} commit{plural})") if commit_count > 0 else ""
        hash_display = gray(f" {hash_str}") if hash_str else ""

        if is_current:
            print(f"  {green(symbols.pointer)} {green(bold(branch))}{hash_display}{commits}{pr_tag}")
        else:
            print(f"  {symbols.circle} {branch}{hash_display}{commits}{pr_tag}")

        # Connector
        if i > 0:
            print(f"  {symbols.line}")

    # Show trunk at bottom
    print(f"  {symbols.line}")
    if current_branch == stack["trunk"]:
        print(f"  {green(symbols.pointer)} {green(bold(stack['trunk']))} {dim('(trunk)')}")
    else:
        trunk_display = stack["trunk"]
        print(f"  {symbols.dot} {dim(trunk_display)} {dim('(trunk)')}")

    print()


def log_all(state: dict, current_branch: str) -> None:
    stacks = state["stacks"]

    if not stacks:
        info("No stacks. Create one with: gs stack new <name>")
        return

    heading("All Stacks")
    print()

    for s in stacks.values():
        is_active = current_branch in s["branches"]
        stack_label = (
            f"{green(symbols.pointer)} {bold(s['name'])}"
            if is_active
            else f"  {s['name']}"
        )
        branch_count = len(s["branches"])
        trunk_name = s["trunk"]
        print(f"{stack_label} {dim(f'({branch_count} branches, base: {trunk_name})')}")

        for i in range(len(s["branches"]) - 1, -1, -1):
            branch = s["branches"][i]
            is_curr = branch == current_branch
            prefix = "    "
            pr_num = state["branches"].get(branch, {}).get("pr_number")
            pr_tag = yellow(f" #{pr_num}") if pr_num else ""

            if is_curr:
                print(f"{prefix}{green(symbols.pointer)} {green(branch)}{pr_tag}")
            else:
                print(f"{prefix}{symbols.circle} {branch}{pr_tag}")

        print()
