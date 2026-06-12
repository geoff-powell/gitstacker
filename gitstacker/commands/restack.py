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
    is_continue = "--continue" in args

    state = load_state()
    current_branch = get_current_branch()

    if is_continue:
        return _restack_continue(state, current_branch)

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


def _restack_continue(state: dict, current_branch: str) -> None:
    """Continue a previously failed restack from where it left off."""
    progress = state.get("_restack_progress")
    if not progress:
        error("No restack in progress. Run `gs restack` to start.")
        raise SystemExit(1)

    stack_name = progress["stack"]
    stack = state["stacks"].get(stack_name)
    if not stack:
        error(f'Stack "{stack_name}" not found. Clearing progress.')
        state.pop("_restack_progress", None)
        save_state(state)
        raise SystemExit(1)

    failed_branch = progress["failed_at"]
    completed = progress.get("completed", [])
    original_branch = progress.get("original_branch", current_branch)

    # Check that we're on the failed branch (user should have resolved conflicts)
    if current_branch != failed_branch:
        warn(f'Expected to be on "{failed_branch}" (the branch with conflicts).')
        info(f"Switch to it and resolve conflicts first: git checkout {failed_branch}")
        raise SystemExit(1)

    info(f"Continuing restack from {bold(failed_branch)}...")
    print()

    # Find the index to continue from (the branch AFTER the failed one)
    branches = stack["branches"]
    try:
        failed_idx = branches.index(failed_branch)
    except ValueError:
        error(f'Branch "{failed_branch}" no longer in stack.')
        state.pop("_restack_progress", None)
        save_state(state)
        raise SystemExit(1)

    # Update commit_base for the branch that was manually resolved
    if failed_branch in state["branches"]:
        parent = get_parent_branch(state, stack, failed_branch)
        state["branches"][failed_branch]["commit_base"] = get_commit_hash(parent)

    # Continue restacking remaining branches (after the failed one)
    continue_idx = failed_idx + 1
    branch_count = len(branches)
    failed = False
    failed_at = ""
    newly_rebased = []

    for i in range(continue_idx, branch_count):
        branch = branches[i]
        parent = get_parent_branch(state, stack, branch)
        meta = state["branches"].get(branch, {})
        old_base = meta.get("commit_base") or parent

        idx_display = dim(f"[{i + 1}/{branch_count}]")
        sys.stdout.write(f"  {idx_display} Rebasing {bold(branch)} onto {parent}...")
        sys.stdout.flush()

        result = rebase_onto(parent, old_base, branch)

        if not result.success:
            print(f" {red('CONFLICT')}")
            rebase_abort()

            sys.stdout.write(f"  {dim('  Trying simple rebase...')}")
            sys.stdout.flush()

            simple_result = git("rebase", parent, branch)
            if simple_result.success:
                print(f" {green('OK')}")
                newly_rebased.append(branch)
                if branch in state["branches"]:
                    state["branches"][branch]["commit_base"] = get_commit_hash(parent)
            else:
                print(f" {red('CONFLICT')}")
                rebase_abort()
                failed = True
                failed_at = branch
                break
        else:
            print(f" {green('OK')}")
            newly_rebased.append(branch)
            if branch in state["branches"]:
                state["branches"][branch]["commit_base"] = get_commit_hash(parent)

    if failed:
        state["_restack_progress"] = {
            "stack": stack_name,
            "failed_at": failed_at,
            "completed": completed + [failed_branch] + newly_rebased,
            "original_branch": original_branch,
        }
        save_state(state)
        print()
        warn(f'Restacking stopped at "{failed_at}" due to conflicts.')
        info("Resolve conflicts, then run `gs restack --continue`.")
    else:
        state.pop("_restack_progress", None)
        save_state(state)
        print()
        success("Stack restacked successfully!")

    # Return to original branch
    try:
        checkout(original_branch)
    except Exception:
        pass
