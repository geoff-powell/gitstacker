"""gs submit - Create or update stacked PRs for the entire stack."""

import sys
from ..git_ops import get_current_branch, push_branch, has_remote_diverged
from ..store import (
    load_state, save_state, get_current_stack, get_parent_branch,
)
from ..github import (
    is_gh_available, get_pr_for_branch, create_pr,
    update_pr_base, update_pr, generate_stack_body,
)
from ..output import (
    success, error, info, heading, bold, green, yellow, cyan, dim,
)


def cmd_submit(args: list[str]) -> None:
    # Check gh CLI
    if not is_gh_available():
        error("GitHub CLI (gh) not found or not authenticated.")
        info("Install: https://cli.github.com")
        info("Auth: gh auth login")
        raise SystemExit(1)

    state = load_state()
    current_branch = get_current_branch()
    draft = "--draft" in args or "-d" in args

    # Find current stack
    stack = get_current_stack(state, current_branch)
    if not stack and state.get("current_stack"):
        stack = state["stacks"].get(state["current_stack"])

    if not stack:
        error("No active stack found.")
        raise SystemExit(1)

    if not stack["branches"]:
        info("Stack has no branches to submit.")
        return

    stack_name = stack["name"]
    heading(f"Submitting stack: {stack_name}")
    print()

    # Push all branches
    info("Pushing branches to remote...")
    force = "--force" in args
    for branch in stack["branches"]:
        sys.stdout.write(f"  {dim('push')} {branch}...")
        sys.stdout.flush()

        # Check for divergence before force-pushing
        if has_remote_diverged(branch):
            if not force:
                print(f" {yellow('DIVERGED')}")
                info(f'  Remote has new commits on "{branch}". Use --force to overwrite.')
                continue

        result = push_branch(branch, force=True)
        if result.success:
            print(f" {green('OK')}")
        else:
            print(f" {yellow('WARN')}: {result.stderr}")
    print()

    # Collect PR numbers for stack description
    pr_numbers: dict[str, int] = {}

    # Create/update PRs from bottom to top
    info("Creating/updating PRs...")
    branch_count = len(stack["branches"])
    for i, branch in enumerate(stack["branches"]):
        parent = get_parent_branch(state, stack, branch)
        meta = state["branches"].get(branch, {})

        idx_display = dim(f"[{i + 1}/{branch_count}]")
        sys.stdout.write(f"  {idx_display} {branch}...")
        sys.stdout.flush()

        # Check if PR already exists
        existing_pr = get_pr_for_branch(branch)

        if existing_pr:
            # Update base if needed
            if existing_pr.base != parent:
                update_pr_base(existing_pr.number, parent)

            # Update metadata
            if branch in state["branches"]:
                state["branches"][branch]["pr_number"] = existing_pr.number
                state["branches"][branch]["pr_url"] = existing_pr.url
            pr_numbers[branch] = existing_pr.number

            print(f" {cyan('updated')} #{existing_pr.number}")
        else:
            # Create new PR
            try:
                # Generate title from branch name
                title = branch.replace("-", " ").replace("_", " ").capitalize()

                body = generate_stack_body(
                    stack_name=stack["name"],
                    branches=stack["branches"],
                    current_branch=branch,
                    pr_numbers=pr_numbers,
                )

                pr = create_pr(
                    title=title,
                    body=body,
                    base=parent,
                    head=branch,
                    draft=draft,
                )

                if branch in state["branches"]:
                    state["branches"][branch]["pr_number"] = pr.number
                    state["branches"][branch]["pr_url"] = pr.url
                pr_numbers[branch] = pr.number

                print(f" {green('created')} #{pr.number}")
            except Exception as e:
                print(f" {yellow('FAILED')}: {e}")

    # Update all PR bodies with complete stack info
    print()
    info("Updating PR descriptions with stack info...")
    for branch in stack["branches"]:
        meta = state["branches"].get(branch, {})
        pr_num = meta.get("pr_number")
        if pr_num:
            body = generate_stack_body(
                stack_name=stack["name"],
                branches=stack["branches"],
                current_branch=branch,
                pr_numbers=pr_numbers,
            )
            update_pr(pr_num, body=body)

    save_state(state)
    print()
    success("Stack submitted!")
    print()

    # Print summary
    for branch in stack["branches"]:
        meta = state["branches"].get(branch, {})
        pr_url = meta.get("pr_url")
        if pr_url:
            print(f"  {bold(branch)} {dim(chr(8594))} {pr_url}")

    print()
