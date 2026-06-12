"""
Stack data model and persistence.
Stores state in .git/gitstacker/state.json
"""

import json
import os
import shutil
from dataclasses import dataclass, field
from typing import Optional
from .git_ops import get_git_root


STATE_FILE = "state.json"
DATA_DIR = "gitstacker"
CONFIG_VERSION = 1


# --- State Schema & Validation ---

_STATE_DEFAULTS = {
    "trunk": "main",
    "stacks": {},
    "branches": {},
    "current_stack": None,
    "version": CONFIG_VERSION,
}


def _validate_state(state: dict) -> dict:
    """Validate and repair state, filling missing keys with defaults.

    Ensures all required keys exist and have correct types.
    Returns the repaired state dict.
    """
    # Fill missing top-level keys
    for key, default in _STATE_DEFAULTS.items():
        if key not in state:
            state[key] = default

    # Type validation & repair
    if not isinstance(state.get("trunk"), str) or not state["trunk"]:
        state["trunk"] = "main"
    if not isinstance(state.get("stacks"), dict):
        state["stacks"] = {}
    if not isinstance(state.get("branches"), dict):
        state["branches"] = {}
    if not isinstance(state.get("version"), int):
        state["version"] = CONFIG_VERSION
    if state.get("current_stack") is not None and not isinstance(state["current_stack"], str):
        state["current_stack"] = None

    # Validate each stack entry
    for name, stack in list(state["stacks"].items()):
        if not isinstance(stack, dict):
            del state["stacks"][name]
            continue
        if "name" not in stack:
            stack["name"] = name
        if "trunk" not in stack or not isinstance(stack["trunk"], str):
            stack["trunk"] = state["trunk"]
        if "branches" not in stack or not isinstance(stack["branches"], list):
            stack["branches"] = []
        if "created_at" not in stack:
            stack["created_at"] = ""

    # Validate each branch entry
    for name, meta in list(state["branches"].items()):
        if not isinstance(meta, dict):
            del state["branches"][name]
            continue
        if "name" not in meta:
            meta["name"] = name
        if "parent" not in meta or not isinstance(meta["parent"], str):
            meta["parent"] = state["trunk"]
        meta.setdefault("pr_number", None)
        meta.setdefault("pr_url", None)
        meta.setdefault("commit_base", None)

    return state


# --- Dataclass definitions (for type reference) ---

@dataclass
class BranchMeta:
    name: str
    parent: str
    pr_number: Optional[int] = None
    pr_url: Optional[str] = None
    commit_base: Optional[str] = None


@dataclass
class StackData:
    name: str
    trunk: str
    branches: list[str] = field(default_factory=list)
    created_at: str = ""


@dataclass
class GitStackerState:
    trunk: str
    stacks: dict[str, dict] = field(default_factory=dict)
    branches: dict[str, dict] = field(default_factory=dict)
    current_stack: Optional[str] = None
    version: int = CONFIG_VERSION


# --- File I/O ---

def _get_data_dir() -> str:
    """Get the .git/gitstacker directory, creating it if needed."""
    root = get_git_root()
    data_dir = os.path.join(root, ".git", DATA_DIR)
    os.makedirs(data_dir, exist_ok=True)
    return data_dir


def _get_state_path() -> str:
    """Get the full path to state.json."""
    return os.path.join(_get_data_dir(), STATE_FILE)


def _backup_state(path: str) -> None:
    """Keep a backup of last known good state for recovery."""
    bak_path = path + ".bak"
    try:
        shutil.copy2(path, bak_path)
    except OSError:
        pass  # Non-critical; best effort backup


def is_initialized() -> bool:
    """Check if gitstacker has been initialized in this repo."""
    try:
        path = _get_state_path()
        return os.path.exists(path)
    except RuntimeError:
        return False


def load_state() -> dict:
    """Load the gitstacker state from disk.

    Validates schema and fills missing keys with defaults.
    Creates a .bak copy on successful load for crash recovery.
    Falls back to .bak if primary state is corrupted.
    """
    path = _get_state_path()

    if not os.path.exists(path):
        raise RuntimeError("GitStacker not initialized. Run `gs init` first.")

    try:
        with open(path, "r") as f:
            state = json.load(f)
    except json.JSONDecodeError as e:
        # Try loading from backup
        bak_path = path + ".bak"
        if os.path.exists(bak_path):
            try:
                with open(bak_path, "r") as f:
                    state = json.load(f)
                # Restore backup as primary
                shutil.copy2(bak_path, path)
            except (json.JSONDecodeError, OSError):
                raise RuntimeError(
                    f"State file is corrupted and backup is unusable: {e}\n"
                    f"  File: {path}\n"
                    f"  Try: rm {path} && gs init"
                )
        else:
            raise RuntimeError(
                f"State file is corrupted (invalid JSON): {e}\n"
                f"  File: {path}\n"
                f"  Try: rm {path} && gs init"
            )

    if not isinstance(state, dict):
        raise RuntimeError(
            f"State file has invalid format (expected object, got {type(state).__name__})\n"
            f"  File: {path}\n"
            f"  Try: rm {path} && gs init"
        )

    # Validate and repair
    state = _validate_state(state)

    # Create backup of good state
    _backup_state(path)

    return state


def save_state(state: dict) -> None:
    """Save the gitstacker state to disk atomically.

    Writes to a temp file first, then uses os.replace() for atomic rename.
    This prevents corruption if the process is killed mid-write.
    """
    path = _get_state_path()
    tmp_path = path + ".tmp"

    try:
        with open(tmp_path, "w") as f:
            json.dump(state, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
    except OSError as e:
        # Clean up temp file on failure (best effort)
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise RuntimeError(f"Failed to save state: {e}")


def init_state(trunk: str) -> dict:
    """Initialize a new gitstacker state."""
    state = {
        "trunk": trunk,
        "stacks": {},
        "branches": {},
        "current_stack": None,
        "version": CONFIG_VERSION,
    }
    save_state(state)
    return state


# --- Query helpers ---

def get_current_stack(state: dict, branch: str) -> Optional[dict]:
    """Get the stack containing the given branch, or None."""
    for stack in state["stacks"].values():
        if branch in stack["branches"]:
            return stack
    return None


def get_branch_position(stack: dict, branch: str) -> int:
    """Get 0-indexed position of branch in the stack."""
    try:
        return stack["branches"].index(branch)
    except ValueError:
        return -1


def get_parent_branch(state: dict, stack: dict, branch: str) -> str:
    """Get the parent of a branch (previous in stack, or trunk)."""
    pos = get_branch_position(stack, branch)
    if pos <= 0:
        return stack["trunk"]
    return stack["branches"][pos - 1]


def get_child_branches(stack: dict, branch: str) -> list[str]:
    """Get branches above this one in the stack."""
    pos = get_branch_position(stack, branch)
    if pos < 0 or pos >= len(stack["branches"]) - 1:
        return []
    return stack["branches"][pos + 1:]


# --- Mutation helpers ---

def add_branch_to_stack(state: dict, stack_name: str, branch_name: str, parent: str) -> None:
    """Add a branch to a stack."""
    stack = state["stacks"].get(stack_name)
    if not stack:
        raise RuntimeError(f'Stack "{stack_name}" not found')
    stack["branches"].append(branch_name)
    state["branches"][branch_name] = {
        "name": branch_name,
        "parent": parent,
        "pr_number": None,
        "pr_url": None,
        "commit_base": None,
    }


def remove_branch_from_stack(state: dict, branch_name: str) -> None:
    """Remove a branch from its stack and update children."""
    stack = get_current_stack(state, branch_name)
    if not stack:
        return

    pos = get_branch_position(stack, branch_name)

    # Update child's parent to point to removed branch's parent
    if pos < len(stack["branches"]) - 1:
        parent = get_parent_branch(state, stack, branch_name)
        child = stack["branches"][pos + 1]
        if child in state["branches"]:
            state["branches"][child]["parent"] = parent

    stack["branches"].pop(pos)
    state["branches"].pop(branch_name, None)


def create_stack(state: dict, name: str, trunk: Optional[str] = None) -> dict:
    """Create a new stack."""
    if name in state["stacks"]:
        raise RuntimeError(f'Stack "{name}" already exists')

    from datetime import datetime

    stack = {
        "name": name,
        "trunk": trunk or state["trunk"],
        "branches": [],
        "created_at": datetime.now().isoformat(),
    }
    state["stacks"][name] = stack
    state["current_stack"] = name
    return stack


def delete_stack(state: dict, name: str) -> None:
    """Delete a stack (doesn't delete git branches)."""
    if name not in state["stacks"]:
        raise RuntimeError(f'Stack "{name}" not found')

    stack = state["stacks"][name]
    for branch in stack["branches"]:
        state["branches"].pop(branch, None)

    del state["stacks"][name]
    if state.get("current_stack") == name:
        state["current_stack"] = None
