# Task 03: Update Comments When Stack Shrinks

## Summary
Change the guard in `submit.py` from `if len(pr_numbers) > 1` to `if pr_numbers` (any PRs at all). This ensures:
- Single-PR stacks still get their navigation comment updated (removing stale multi-PR data)
- When a stack shrinks from 3 PRs to 1, the remaining PR's comment reflects the current state

## Files to Modify
- `gitstacker/commands/submit.py`

## Implementation Details

Change line 149 from:
```python
if len(pr_numbers) > 1:
```

To:
```python
if pr_numbers:
```

The `generate_stack_comment` function already handles single-branch stacks correctly — it will show just one entry with "← this PR". This is still useful as it identifies the branch as part of a gitstacker-managed stack.

## Acceptance Criteria
- [ ] Stack navigation comments are updated even for single-PR stacks
- [ ] A stack that previously had 3 PRs but now has 1 gets its comment updated
- [ ] No behavioral change for multi-PR stacks
