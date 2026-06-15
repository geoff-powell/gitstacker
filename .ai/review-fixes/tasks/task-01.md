# Task 01: Seed pr_numbers from Saved State

## Summary
Pre-populate the `pr_numbers` dict from `state["branches"]` before the PR creation/update loop in `submit.py`. This ensures that if `get_pr_for_branch()` fails for a branch (network blip, rate limit), existing PR numbers are still available for stack body generation and comment navigation.

## Files to Modify
- `gitstacker/commands/submit.py`

## Implementation Details

In `cmd_submit()`, after the line `pr_numbers: dict[str, int] = {}` (line 69), add logic to seed from state:

```python
pr_numbers: dict[str, int] = {}
# Seed from saved state so network failures don't lose existing PR references
for branch in stack["branches"]:
    meta = state["branches"].get(branch, {})
    if meta.get("pr_number"):
        pr_numbers[branch] = meta["pr_number"]
```

This ensures:
- Stack body and navigation comments always show all known PRs
- If `get_pr_for_branch` returns None due to transient failure, we still have the number
- Fresh runs (no state) work exactly as before since the dict starts empty

## Acceptance Criteria
- [ ] `pr_numbers` is pre-seeded from state before the loop
- [ ] Existing behavior is unchanged when state has no PR numbers
- [ ] PR numbers discovered during the run still override stale state values
