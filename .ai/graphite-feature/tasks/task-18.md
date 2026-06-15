# Task 18: Create Undo Journal Infrastructure (`journal.py`)

## Description
Create a new `gitstacker/journal.py` module that manages an undo journal stored at `.git/gitstacker/journal.json`. This journal captures pre-operation state snapshots (state.json + branch SHAs) before any mutating command executes, enabling `gs undo` to restore previous states.

## Dependencies
- None (foundational module)

## Affected Files
- `gitstacker/journal.py` — **new** (journal I/O and snapshot logic)
- `gitstacker/git_ops.py` — add `get_all_branch_shas()` helper

## Implementation Details

### New file: `gitstacker/journal.py`

```python
"""
Undo journal — captures pre-operation state for gs undo.
Stores journal entries in .git/gitstacker/journal.json.
"""

import copy
import json
import os
from datetime import datetime
from typing import Optional

from .git_ops import get_current_branch, get_commit_hash, git, get_git_root
from .store import _get_data_dir

JOURNAL_FILE = "journal.json"
MAX_ENTRIES = 10


def _get_journal_path() -> str:
    """Get the full path to journal.json."""
    return os.path.join(_get_data_dir(), JOURNAL_FILE)


def load_journal() -> list[dict]:
    """Load the journal from disk. Returns empty list if missing/corrupt."""
    path = _get_journal_path()
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r") as f:
            entries = json.load(f)
        if not isinstance(entries, list):
            return []
        return entries
    except (json.JSONDecodeError, OSError):
        return []


def save_journal(entries: list[dict]) -> None:
    """Save journal atomically (same pattern as store.py)."""
    path = _get_journal_path()
    tmp_path = path + ".tmp"
    try:
        with open(tmp_path, "w") as f:
            json.dump(entries, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
    except OSError as e:
        raise RuntimeError(f"Failed to save journal: {e}")


def snapshot_before(operation: str, state: dict) -> None:
    """Capture pre-operation snapshot. Call at start of mutating commands.
    
    Args:
        operation: Command name (e.g., "create", "modify", "restack")
        state: Current state dict (will be deep-copied into journal)
    """
    from .git_ops import get_current_branch, get_commit_hash, git
    
    # Get current HEAD info
    try:
        head_branch = get_current_branch()
    except RuntimeError:
        head_branch = "HEAD"
    
    try:
        head_sha = get_commit_hash("HEAD")
    except RuntimeError:
        head_sha = ""
    
    # Capture SHAs for all tracked branches
    branch_shas = {}
    for branch_name in state.get("branches", {}):
        try:
            branch_shas[branch_name] = get_commit_hash(branch_name)
        except RuntimeError:
            pass  # Branch may not exist in git yet
    
    entry = {
        "operation": operation,
        "timestamp": datetime.now().isoformat(),
        "pre_state": copy.deepcopy(state),
        "branch_shas": branch_shas,
        "head_branch": head_branch,
        "head_sha": head_sha,
    }
    
    # Load existing, prepend new entry, truncate
    journal = load_journal()
    journal.insert(0, entry)
    journal = journal[:MAX_ENTRIES]
    save_journal(journal)


def get_last_entry() -> Optional[dict]:
    """Get the most recent journal entry, or None if empty."""
    journal = load_journal()
    return journal[0] if journal else None


def remove_last_entry() -> None:
    """Remove the most recent journal entry after successful undo."""
    journal = load_journal()
    if journal:
        journal.pop(0)
        save_journal(journal)
```

### Addition to `gitstacker/git_ops.py`

Add this function at the end of the file:

```python
def get_all_branch_shas(branches: list[str]) -> dict[str, str]:
    """Get commit SHAs for a list of branches. Skips branches that don't exist."""
    shas = {}
    for branch in branches:
        result = git("rev-parse", branch)
        if result.success:
            shas[branch] = result.stdout
    return shas


def reset_branch_to_sha(branch: str, sha: str) -> GitResult:
    """Force-reset a branch pointer to a specific SHA without checking it out."""
    return git("branch", "-f", branch, sha)
```

## Acceptance Criteria
- [ ] `gitstacker/journal.py` exists with all functions above
- [ ] `load_journal()` returns `[]` when file doesn't exist
- [ ] `load_journal()` returns `[]` when file is corrupt JSON
- [ ] `save_journal()` writes atomically (temp file + os.replace)
- [ ] `snapshot_before()` captures: operation, timestamp, deep-copied state, branch SHAs, HEAD info
- [ ] Journal is truncated to 10 entries max
- [ ] `get_last_entry()` returns most recent entry
- [ ] `remove_last_entry()` removes the first (most recent) entry
- [ ] `get_all_branch_shas()` added to `git_ops.py`
- [ ] `reset_branch_to_sha()` added to `git_ops.py`
- [ ] No import errors when module is loaded
