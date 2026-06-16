# Plan: Replace `gs create` with `gs track`

## Overview

Replace the `gs create` command (which creates a new git branch AND adds it to a stack) with a `gs track` command that tracks **existing** branches into stacks. This mirrors Graphite's workflow where users create branches normally with git, then use the stacking tool to track them.

## Design

### New Workflow
```bash
# Old workflow (being deprecated)
gs create auth-api         # creates branch + adds to stack

# New workflow
git checkout -b auth-api   # user creates branch with git
gs track                   # tracks current branch into active stack
```

### Parent Detection Algorithm
1. Get all local branches (tracked + untracked)
2. For each candidate branch, check if it's a direct ancestor of the target
   - `merge_base(candidate, target) == commit_hash(candidate)` → candidate is ancestor
3. Compute distance: `commit_count(candidate, target)`
4. Pick the closest ancestor (smallest distance)
5. If multiple branches at the same distance → **interactive prompt** for user to choose
6. If parent is not trunk and not tracked → offer to walk-up track it recursively

### Auto-Track Guards
When a user runs a stack manipulation command (`gs up`, `gs down`, `gs modify`, `gs restack`, `gs submit`, etc.) on an untracked branch, instead of just erroring, offer to track the branch first.

## Tasks (Sequential — one stack)

| # | Description | Files |
|---|-------------|-------|
| 01 | Add git_ops helpers for parent detection | `git_ops.py` |
| 02 | Create core `gs track` command | `commands/track.py` |
| 03 | Deprecate `gs create` with warning | `commands/create.py` |
| 04 | Add auto-track guards to stack commands | `store.py`, navigation/modify/restack |
| 05 | Update CLI, help, aliases, completions | `cli.py`, `aliases.py`, `completions.py` |

## Architecture Decisions

1. **Parent detection uses merge-base** — reliable for linear histories and simple branch topologies
2. **Interactive prompts via stdin** — only when ambiguous (multiple candidate parents at same distance)
3. **Walk-up is recursive** — if detecting parent finds an untracked branch, offer to track it too (depth-first)
4. **Auto-track is opt-in per invocation** — user gets a y/n prompt, not forced
5. **Deprecation, not removal** — `gs create` still works but prints a warning suggesting `gs track`

## Acceptance Criteria

1. `gs track` on current branch detects correct parent and adds to active stack
2. `gs track <name>` tracks a named branch
3. If no stack exists, prompts user to create one (or errors clearly)
4. If parent is ambiguous (multiple branches at fork commit), prompts user to choose
5. If parent is untracked and not trunk, offers to track it first (walk-up)
6. `gs create` works but prints deprecation warning
7. Stack commands on untracked branches prompt to track instead of just erroring
8. All existing tests pass (with updates to tests that use `create`)
