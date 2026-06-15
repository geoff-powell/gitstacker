"""
GitHub integration — create and manage stacked PRs via `gh` CLI.
"""

import json
import subprocess
from dataclasses import dataclass
from typing import Optional


STACK_COMMENT_MARKER = "<!-- gitstacker:stack-comment -->"


@dataclass
class GhResult:
    stdout: str
    stderr: str
    returncode: int

    @property
    def success(self) -> bool:
        return self.returncode == 0


def gh(*args: str) -> GhResult:
    """Run a gh CLI command."""
    result = subprocess.run(
        ["gh", *args],
        capture_output=True,
        text=True,
    )
    return GhResult(
        stdout=result.stdout.strip(),
        stderr=result.stderr.strip(),
        returncode=result.returncode,
    )


def is_gh_available() -> bool:
    """Check if gh CLI is installed and authenticated."""
    return gh("auth", "status").success


@dataclass
class PrInfo:
    number: int
    url: str
    title: str
    state: str
    base: str
    head: str


def get_pr_for_branch(branch: str) -> Optional[PrInfo]:
    """Get PR info for a branch, or None if no PR exists."""
    result = gh(
        "pr", "view", branch,
        "--json", "number,url,title,state,baseRefName,headRefName"
    )
    if not result.success:
        return None

    data = json.loads(result.stdout)
    return PrInfo(
        number=data["number"],
        url=data["url"],
        title=data["title"],
        state=data["state"],
        base=data["baseRefName"],
        head=data["headRefName"],
    )


def create_pr(
    title: str,
    body: str,
    base: str,
    head: str,
    draft: bool = False,
) -> PrInfo:
    """Create a new pull request."""
    args = [
        "pr", "create",
        "--title", title,
        "--body", body,
        "--base", base,
        "--head", head,
    ]
    if draft:
        args.append("--draft")

    result = gh(*args)
    if not result.success:
        raise RuntimeError(f"Failed to create PR: {result.stderr}")

    url = result.stdout.strip()

    # Try to fetch full PR info
    info = get_pr_for_branch(head)
    if info:
        return info

    # Fallback: parse URL for PR number
    import re
    match = re.search(r"/pull/(\d+)", url)
    if not match:
        raise RuntimeError(
            f"PR created but could not determine PR number from URL: {url}"
        )

    return PrInfo(
        number=int(match.group(1)),
        url=url,
        title=title,
        state="OPEN",
        base=base,
        head=head,
    )


def update_pr_base(pr_number: int, new_base: str) -> bool:
    """Update the base branch of a PR."""
    return gh("pr", "edit", str(pr_number), "--base", new_base).success


def update_pr(pr_number: int, title: Optional[str] = None, body: Optional[str] = None) -> bool:
    """Update PR title and/or body."""
    args = ["pr", "edit", str(pr_number)]
    if title:
        args.extend(["--title", title])
    if body:
        args.extend(["--body", body])
    return gh(*args).success


def generate_stack_body(
    stack_name: str,
    branches: list[str],
    current_branch: str,
    pr_numbers: dict[str, int],
    description: Optional[str] = None,
) -> str:
    """Generate the PR body with stack visualization."""
    lines: list[str] = []

    if description:
        lines.append(description)
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("**Stack:**")
    lines.append("")

    for i in range(len(branches) - 1, -1, -1):
        branch = branches[i]
        is_current = branch == current_branch
        pr_num = pr_numbers.get(branch)
        pr_ref = f" (#{pr_num})" if pr_num else ""
        marker = " \U0001f448" if is_current else ""
        lines.append(f"{i + 1}. `{branch}`{pr_ref}{marker}")

    lines.append("")
    lines.append("_Managed by [GitStacker](https://github.com/gitstacker/gitstacker)_")

    return "\n".join(lines)


# --- Stack comment management ---


def _get_repo_nwo() -> Optional[str]:
    """Get the owner/repo (name with owner) for the current repo."""
    result = gh("repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner")
    if result.success:
        return result.stdout.strip()
    return None


def _find_stack_comment(pr_number: int) -> Optional[int]:
    """Find the gitstacker stack comment on a PR. Returns comment ID or None."""
    result = gh(
        "api", f"repos/{{owner}}/{{repo}}/issues/{pr_number}/comments",
        "--paginate",
        "--jq", f'[.[] | select(.body | contains("{STACK_COMMENT_MARKER}"))][0].id',
    )
    if not result.success or not result.stdout.strip():
        return None

    try:
        comment_id = int(result.stdout.strip())
        return comment_id
    except (ValueError, TypeError):
        return None


def _create_comment(pr_number: int, body: str) -> bool:
    """Create a new comment on a PR."""
    result = gh("pr", "comment", str(pr_number), "--body", body)
    return result.success


def _update_comment(comment_id: int, body: str) -> bool:
    """Update an existing comment by ID."""
    result = gh(
        "api", "repos/{owner}/{repo}/issues/comments/" + str(comment_id),
        "-X", "PATCH",
        "-f", f"body={body}",
    )
    return result.success


def generate_stack_comment(
    stack_name: str,
    branches: list[str],
    current_branch: str,
    pr_numbers: dict[str, int],
    pr_urls: dict[str, str],
) -> str:
    """Generate the stack navigation comment body for a specific PR.

    Shows the full stack with links to each PR, marking the current one.
    """
    lines: list[str] = []
    lines.append(f"### \U0001f4da Stack: `{stack_name}`")
    lines.append("")

    for i in range(len(branches) - 1, -1, -1):
        branch = branches[i]
        is_current = branch == current_branch
        pr_num = pr_numbers.get(branch)
        pr_url = pr_urls.get(branch)

        if pr_num and pr_url:
            pr_link = f"[#{pr_num}]({pr_url})"
        elif pr_num:
            pr_link = f"#{pr_num}"
        else:
            pr_link = "_no PR_"

        if is_current:
            lines.append(f"- **{i + 1}. `{branch}` \u2190 this PR** ({pr_link})")
        else:
            lines.append(f"- {i + 1}. `{branch}` ({pr_link})")

    lines.append("")
    lines.append(dim_text("Managed by GitStacker \u00b7 comment auto-updated on each `gs submit`"))
    lines.append("")
    lines.append(STACK_COMMENT_MARKER)

    return "\n".join(lines)


def upsert_stack_comment(
    pr_number: int,
    stack_name: str,
    branches: list[str],
    current_branch: str,
    pr_numbers: dict[str, int],
    pr_urls: dict[str, str],
) -> bool:
    """Create or update the stack navigation comment on a PR.

    At most one gitstacker comment will exist per PR. If one already
    exists (identified by the hidden marker), it is updated in place.
    """
    body = generate_stack_comment(
        stack_name=stack_name,
        branches=branches,
        current_branch=current_branch,
        pr_numbers=pr_numbers,
        pr_urls=pr_urls,
    )

    # Try to find existing comment
    existing_id = _find_stack_comment(pr_number)

    if existing_id:
        return _update_comment(existing_id, body)
    else:
        return _create_comment(pr_number, body)


def dim_text(text: str) -> str:
    """Wrap text in a dim/small HTML tag for GitHub markdown."""
    return f"<sub>{text}</sub>"
