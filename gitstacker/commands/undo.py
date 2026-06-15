"""gs undo - Revert the last mutating GitStacker operation."""

from ..journal import get_last_entry, remove_last_entry, snapshot_before, load_journal, save_journal
from ..store import save_state, load_state
from ..git_ops import (
    get_current_branch, checkout, is_working_tree_clean,
    reset_branch_to_sha, git,
)
from ..output import success, error, info, warn, bold, dim


def cmd_undo(args: list[str]) -> None:
    """Undo the last mutating operation."""

    # Check for dirty tree
    if not is_working_tree_clean():
        error("Working tree has uncommitted changes.")
        info("Commit or stash your changes before undoing.")
        raise SystemExit(1)

    # Get last journal entry
    entry = get_last_entry()
    if not entry:
        error("Nothing to undo.")
        info("The undo journal is empty — no mutating operations have been recorded.")
        raise SystemExit(1)

    operation = entry.get("operation", "unknown")
    timestamp = entry.get("timestamp", "unknown")

    # Show what will be undone
    print()
    info(f"Undoing {bold(operation)} from {dim(timestamp)}...")
    print()

    # Before undoing, snapshot current state (so undo-of-undo works)
    try:
        current_state = load_state()
        snapshot_before("undo", current_state)
    except RuntimeError:
        pass  # State might be in a bad place; proceed anyway

    # Restore state.json
    pre_state = entry.get("pre_state")
    if pre_state:
        save_state(pre_state)
        info("Restored state.json")
    else:
        warn("No state snapshot found in journal entry — state not restored.")

    # Restore branch positions
    branch_shas = entry.get("branch_shas", {})
    restored_count = 0
    skipped = []

    for branch, sha in branch_shas.items():
        # Verify SHA is reachable
        verify = git("cat-file", "-t", sha)
        if not verify.success:
            skipped.append(branch)
            continue

        result = reset_branch_to_sha(branch, sha)
        if result.success:
            restored_count += 1
        else:
            skipped.append(branch)

    if restored_count > 0:
        info(f"Reset {restored_count} branch(es) to previous positions")

    if skipped:
        warn(f"Could not restore: {', '.join(skipped)} (SHAs unreachable or branch conflicts)")

    # Return to the original HEAD position
    head_branch = entry.get("head_branch")
    if head_branch and head_branch != "HEAD":
        try:
            checkout(head_branch)
            info(f"Returned to: {bold(head_branch)}")
        except RuntimeError as e:
            warn(f"Could not checkout {head_branch}: {e}")

    # Remove the consumed entry (the one we just undid)
    # Note: snapshot_before("undo") already added a new entry at position 0,
    # so the entry we consumed is now at position 1
    journal = load_journal()
    if len(journal) > 1:
        journal.pop(1)  # Remove the consumed entry (shifted to pos 1 by snapshot_before)
        save_journal(journal)

    print()
    success(f"Undid {bold(operation)} successfully!")
