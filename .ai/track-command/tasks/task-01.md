# Task 01: Add Git Ops Helpers for Parent Detection

## Summary
Add utility functions to `git_ops.py` that support the parent detection algorithm needed by `gs track`.

## Files to Modify
- `gitstacker/git_ops.py`

## Functions to Add

### `is_ancestor(potential_ancestor: str, branch: str) -> bool`
Check if `potential_ancestor`'s HEAD is a direct ancestor of `branch`'s HEAD.

```python
def is_ancestor(potential_ancestor: str, branch: str) -> bool:
    """Check if potential_ancestor is a direct ancestor of branch."""
    result = git("merge-base", "--is-ancestor", potential_ancestor, branch)
    return result.success
```

### `get_branches_containing_commit(sha: str) -> list[str]`
Get all local branches whose HEAD contains the given commit.

```python
def get_branches_containing_commit(sha: str) -> list[str]:
    """Get local branches that contain the given commit."""
    result = git("branch", "--contains", sha, "--format=%(refname:short)")
    if not result.success:
        return []
    return [b for b in result.stdout.split("\n") if b]
```

### `get_branches_at_commit(sha: str) -> list[str]`
Get all local branches whose HEAD **points to** the given commit (not just contains it).

```python
def get_branches_at_commit(sha: str) -> list[str]:
    """Get local branches whose tip IS the given commit."""
    result = git("branch", "--points-at", sha, "--format=%(refname:short)")
    if not result.success:
        return []
    return [b for b in result.stdout.split("\n") if b]
```

## Acceptance Criteria
- [ ] `is_ancestor` correctly identifies ancestor relationships
- [ ] `get_branches_containing_commit` returns branches containing a commit
- [ ] `get_branches_at_commit` returns only branches whose HEAD is exactly at a commit
- [ ] All existing tests continue to pass
