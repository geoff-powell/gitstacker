"""
Git operations wrapper — executes git commands and returns typed results.
Zero external dependencies, uses subprocess only.
"""

import subprocess
from dataclasses import dataclass
from typing import Optional


@dataclass
class GitResult:
    stdout: str
    stderr: str
    returncode: int

    @property
    def success(self) -> bool:
        return self.returncode == 0


def git(*args: str, cwd: Optional[str] = None) -> GitResult:
    """Run a git command and return the result."""
    result = subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
        cwd=cwd,
    )
    return GitResult(
        stdout=result.stdout.strip(),
        stderr=result.stderr.strip(),
        returncode=result.returncode,
    )


def git_or_throw(*args: str, cwd: Optional[str] = None) -> str:
    """Run a git command, raise on failure, return stdout."""
    result = git(*args, cwd=cwd)
    if not result.success:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr}")
    return result.stdout


def get_current_branch() -> str:
    """Get the current branch name."""
    return git_or_throw("rev-parse", "--abbrev-ref", "HEAD")


def get_git_root() -> str:
    """Get the git repository root directory."""
    return git_or_throw("rev-parse", "--show-toplevel")


def is_git_repo() -> bool:
    """Check if we're inside a git repository."""
    return git("rev-parse", "--is-inside-work-tree").success


def get_default_branch() -> str:
    """Detect the default branch (main or master)."""
    result = git("symbolic-ref", "refs/remotes/origin/HEAD")
    if result.success:
        return result.stdout.replace("refs/remotes/origin/", "")

    if git("rev-parse", "--verify", "main").success:
        return "main"
    if git("rev-parse", "--verify", "master").success:
        return "master"
    return "main"


def branch_exists(name: str) -> bool:
    """Check if a branch exists locally."""
    return git("rev-parse", "--verify", name).success


def create_branch(name: str) -> None:
    """Create and switch to a new branch at current HEAD."""
    git_or_throw("checkout", "-b", name)


def checkout(name: str) -> None:
    """Switch to an existing branch."""
    git_or_throw("checkout", name)


def rebase_onto(new_base: str, old_base: str, branch: str) -> GitResult:
    """Rebase branch onto new_base, replaying commits from old_base."""
    return git("rebase", "--onto", new_base, old_base, branch)


def get_merge_base(a: str, b: str) -> str:
    """Get the merge base between two refs."""
    return git_or_throw("merge-base", a, b)


def get_commit_hash(ref: str) -> str:
    """Get the full commit hash for a ref."""
    return git_or_throw("rev-parse", ref)


def get_short_hash(ref: str) -> str:
    """Get the short commit hash for a ref."""
    return git_or_throw("rev-parse", "--short", ref)


def get_commit_count(from_ref: str, to_ref: str) -> int:
    """Get commit count between two refs."""
    result = git("rev-list", "--count", f"{from_ref}..{to_ref}")
    if not result.success:
        return 0
    return int(result.stdout)


def get_log_oneline(from_ref: str, to_ref: str) -> list[str]:
    """Get one-line log between two refs."""
    result = git("log", "--oneline", f"{from_ref}..{to_ref}")
    if not result.success or not result.stdout:
        return []
    return [line for line in result.stdout.split("\n") if line]


def is_working_tree_clean() -> bool:
    """Check if the working tree has no uncommitted changes."""
    result = git("status", "--porcelain")
    return result.success and result.stdout == ""


def stash_push() -> bool:
    """Stash uncommitted changes."""
    return git("stash", "push", "-m", "gitstacker-auto-stash").success


def stash_pop() -> bool:
    """Pop the most recent stash."""
    return git("stash", "pop").success


def fetch_remote() -> None:
    """Fetch from remote with prune."""
    git_or_throw("fetch", "--prune")


def push_branch(branch: str, force: bool = False) -> GitResult:
    """Push a branch to origin."""
    args = ["push", "-u", "origin", branch]
    if force:
        args.insert(1, "--force-with-lease")
    return git(*args)


def list_branches() -> list[str]:
    """List all local branches."""
    result = git("branch", "--format=%(refname:short)")
    if not result.success:
        return []
    return [b for b in result.stdout.split("\n") if b]


def rebase_abort() -> None:
    """Abort a rebase in progress."""
    git("rebase", "--abort")


def pull_rebase(branch: str) -> GitResult:
    """Pull with rebase from origin."""
    return git("pull", "--rebase", "origin", branch)


def has_remote_diverged(branch: str) -> bool:
    """Check if remote branch has commits not in local branch.

    Returns True if remote has diverged (someone else pushed).
    """
    result = git("rev-list", "--count", f"{branch}..origin/{branch}")
    if not result.success:
        return False  # No remote branch yet
    return int(result.stdout) > 0
