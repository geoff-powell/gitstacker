# Task 02: Create Core `gs track` Command

## Summary
Implement the `gs track [branch]` command that tracks an existing git branch into the active stack, auto-detecting its parent branch.

## Files to Create
- `gitstacker/commands/track.py`

## Algorithm

### `detect_parent(target: str, trunk: str, known_branches: list[str]) -> str | list[str]`
1. Collect all local branches (excluding target itself)
2. For each branch, check if it's a direct ancestor of target using `is_ancestor()`
3. For ancestors, compute commit distance: `get_commit_count(candidate, target)`
4. Sort by distance (closest first)
5. If one clear winner → return it
6. If multiple at same distance → return list (caller will prompt)
7. If no ancestors found → return trunk

### `cmd_track(args: list[str]) -> None`
1. Determine target branch (args[0] or current branch)
2. Validate: branch must exist, must not already be tracked
3. Load state, find active stack (or error if none)
4. Call `detect_parent()` to find parent
5. If ambiguous (list returned) → interactive prompt to choose
6. If parent is not trunk and not tracked → offer walk-up tracking:
   - "Branch `<parent>` is not tracked. Track it first? [Y/n]"
   - If yes → recursively track parent first (with its own parent detection)
7. Add branch to stack after parent (insert at correct position)
8. Set `commit_base` = merge_base(parent, target)
9. Save state

### Walk-Up Tracking
When the detected parent is not trunk and not already in a stack:
```
User runs: gs track feature-c
Detected parent: feature-b (not tracked, not trunk)
→ Prompt: "Branch 'feature-b' is not tracked. Track it first? [Y/n]"
→ If Y: detect parent of feature-b → might be trunk (done) or another untracked branch (recurse)
→ After feature-b is tracked, track feature-c with parent=feature-b
```

### Insert Position
When tracking a branch, it must be inserted at the correct position in the stack's branch list:
- If parent is trunk → insert at position 0 (or after any already-tracked branches that are also children of trunk... actually, append to end if parent is the last tracked branch or trunk)
- If parent is a tracked branch → insert right after parent in the list

Wait — simpler: always insert immediately after the parent's position in the branch list. If parent is trunk, insert at position 0. If parent is branch at position N, insert at position N+1. But we need to shift existing entries. Actually the existing `add_branch_to_stack` appends to the end. For track, we need a new helper that inserts at a specific position.

## Interactive Prompt Format
```
Multiple branches found at the fork point:
  1. feature-a
  2. develop
  3. experiment

Which branch is the parent of 'feature-c'? [1-3]: 
```

## Acceptance Criteria
- [ ] `gs track` tracks current branch into active stack
- [ ] `gs track <name>` tracks a named branch
- [ ] Parent is auto-detected correctly for simple linear histories
- [ ] Ambiguous parents trigger an interactive prompt
- [ ] Walk-up tracking recursively tracks intermediate branches
- [ ] Branch is inserted at correct position in stack (after parent)
- [ ] Already-tracked branches produce a clear error
- [ ] No active stack produces a clear error
- [ ] Frozen parent branches are rejected
