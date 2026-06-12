"""gs restack - Rebase all branches in the current stack sequentially."""

from ..git_ops import (
    get_current_branch, checkout, get_commit_hash,
    is_working_tree_clean, stash_push,
    rebase_abort, rebase_onto,
)
from ..git_ops import git
from ..store import (
    load_state, save_state, get_current_stack, get_parent_branch,
)
from ..output import success, error, info, warn, bold, green, red, yellow, dim
import sys


def cmd_restack(args: list[str]) -> None:
    state = load_state()
    current_branch = get_current_branch()

    # Find current stack
    stack = get_current_stack(state, current_branch)
    if not stack and state.get("current_stack"):
        stack = state["stacks"].get(state["current_stack"])

    if not stack:
        error("No active stack found. Use `gs stack switch <name>` to select one.")
        raise SystemExit(1)

    if not stack["branches"]:
        info("Stack has no branches to restack.")
        return

    # Check working tree
    did_stash = False
    if not is_working_tree_clean():
        info("Stashing uncommitted changes...")
        did_stash = stash_push()
        if not did_stash:
            error("Failed to stash changes. Please commit or stash manually.")
            raise SystemExit(1)

    print()
    stack_name = stack["name"]
    branch_count = len(stack["branches"])
    info(f"Restacking {bold(stack_name)} ({branch_count} branches)...")
    print()

    failed = False
    failed_branch = ""
    successfully_rebased = []

    for i, branch in enumerate(stack["branches"]):
        parent = get_parent_branch(state, stack, branch)
        meta = state["branches"].get(branch, {})

        # Old base for --onto rebase
        old_base = meta.get("commit_base") or parent

        idx_display = dim(f"[{i + 1}/{branch_count}]")
        sys.stdout.write(f"  {idx_display} Rebasing {bold(branch)} onto {parent}...")
        sys.stdout.flush()

        # Perform rebase
        result = rebase_onto(parent, old_base, branch)

        if not result.success:
            print(f" {red('CONFLICT')}")

            # Abort and try simple rebase
            rebase_abort()

            sys.stdout.write(f"  {dim('  Trying simple rebase...')}")
            sys.stdout.flush()

            simple_result = git("rebase", parent, branch)
            if simple_result.success:
                print(f" {green('OK')}")
                successfully_rebased.append(branch)
                if branch in state["branches"]:
                    state["branches"][branch]["commit_base"] = get_commit_hash(parent)
            else:
                print(f" {red('CONFLICT')}")
                rebase_abort()
                failed = True
                failed_branch = branch
                # Do NOT update state for this branch
                break
        else:
            print(f" {green('OK')}")
            successfully_rebased.append(branch)
            # Update commit base
            if branch in state["branches"]:
                state["branches"][branch]["commit_base"] = get_commit_hash(parent)

    # Store or clear restack progress
    if failed:
        state["_restack_progress"] = {
            "stack": stack["name"],
            "failed_at": failed_branch,
            "completed": successfully_rebased,
            "original_branch": current_branch,
        }
    else:
        state.pop("_restack_progress", None)

    # Always save state (only successfully rebased branches had commit_base updated)
    save_state(state)

    if not failed:
        print()
        success("Stack restacked successfully!")
    else:
        print()
        warn(f'Restacking stopped at "{failed_branch}" due to conflicts.')
        info(f"Successfully rebased: {len(successfully_rebased)}/{branch_count} branches")
        info("Resolve conflicts manually, then run `gs restack` again.")

    # Return to original branch
    try:
        checkout(current_branch)
    except Exception:
        if stack["branches"]:
            checkout(stack["branches"][-1])

    # Pop stash safely
    if did_stash:
        info("Restoring stashed changes...")
        pop_result = git("stash", "pop")
        if not pop_result.success:
            warn("Could not automatically restore stashed changes.")
            info("Your changes are still in the stash. Run `git stash pop` manually.")
            info(f"Stash error: {pop_result.stderr}")
