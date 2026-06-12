# Task 01: Atomic State Writes + State Validation

## Description
Fix the two critical data corruption bugs in `store.py`: (1) non-atomic writes that can corrupt `state.json` on crash/kill, and (2) missing schema validation on load that causes `KeyError` on malformed state. These are foundational fixes that all other work depends on.

## Files to Create/Modify
- `gitstacker/store.py` — Add atomic write via temp file + `os.replace()`, add schema validation with defaults

## Implementation Details

### Atomic Writes
Replace the current `save_state()` implementation:

```python
def save_state(state: dict) -> None:
    """Save the gitstacker state to disk atomically."""
    path = _get_state_path()
    tmp_path = path + ".tmp"
    with open(tmp_path, "w") as f:
        json.dump(state, f, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_path, path)
```

Key points:
- Write to `state.json.tmp` first
- Call `f.flush()` and `os.fsync()` to ensure data hits disk
- Use `os.replace()` which is atomic on POSIX (and nearly atomic on Windows)

### State Validation
Add a `_validate_state()` function called from `load_state()`:

```python
_STATE_SCHEMA = {
    "trunk": str,
    "stacks": dict,
    "branches": dict,
    "current_stack": (str, type(None)),
    "version": int,
}

_STATE_DEFAULTS = {
    "trunk": "main",
    "stacks": {},
    "branches": {},
    "current_stack": None,
    "version": CONFIG_VERSION,
}

def _validate_state(state: dict) -> dict:
    """Validate and repair state, filling in missing keys with defaults."""
    for key, default in _STATE_DEFAULTS.items():
        if key not in state:
            state[key] = default
    # Validate types
    if not isinstance(state.get("stacks"), dict):
        state["stacks"] = {}
    if not isinstance(state.get("branches"), dict):
        state["branches"] = {}
    return state
```

Update `load_state()` to call `_validate_state()` after `json.load()`.

### State Backup
On successful load, copy `state.json` to `state.json.bak` so there's a recovery point:

```python
def _backup_state(path: str) -> None:
    """Keep a backup of last known good state."""
    import shutil
    bak_path = path + ".bak"
    try:
        shutil.copy2(path, bak_path)
    except OSError:
        pass
```

## Dependencies
- Depends on: none

## Acceptance Criteria
- [ ] `save_state()` writes to a temp file and uses `os.replace()` for atomic rename
- [ ] `save_state()` calls `fsync` before rename to ensure durability
- [ ] `load_state()` fills in missing keys with defaults instead of raising KeyError
- [ ] `load_state()` handles malformed types (e.g., `stacks` is a list instead of dict)
- [ ] A `.bak` file is created on successful load for recovery
- [ ] If `state.json` is corrupted JSON, a helpful error message is shown (not a raw traceback)
- [ ] Existing tests (if any) still pass

## Notes
- `os.replace()` is atomic on POSIX systems. On Windows it's atomic if the filesystem supports it.
- The temp file should be in the same directory as `state.json` so `os.replace()` works (same filesystem).
- Don't remove the existing `.tmp` file on failure — it may aid debugging.
- Consider catching `json.JSONDecodeError` in `load_state()` and attempting to load from `.bak`.
