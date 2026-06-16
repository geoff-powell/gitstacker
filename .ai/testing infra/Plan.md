@@ -1,157 +0,0 @@
# Plan: Testing Infrastructure & Bug Fixes for GitStacker

## Overview

Add comprehensive testing infrastructure to GitStacker and fix critical bugs identified during code review. The goal is to ensure the stacking workflow is reliable for daily SWE use and to prevent regressions as features are added.

---

## Architecture Decisions

### Testing Framework
- **pytest** — industry standard, excellent fixture system, `tmp_path` for temp git repos
- **No external mocking libraries** — use `unittest.mock` (stdlib) for subprocess mocking in unit tests
- **Real git repos for integration tests** — use `tmp_path` fixtures that create actual git repos to test the full flow
- **pytest-cov** for coverage reporting

### Test Organization
```
tests/
├── conftest.py              # Shared fixtures (git_repo, initialized_repo, stacked_repo)
├── unit/
│   ├── test_store.py        # State CRUD, validation, edge cases
│   ├── test_git_ops.py      # Git command construction & error handling
│   ├── test_output.py       # Color/formatting utilities
│   └── test_github.py       # PR body generation, gh command construction
├── integration/
│   ├── test_init.py         # gs init in various repo states
│   ├── test_create.py       # Branch creation scenarios
│   ├── test_navigate.py     # up/down/top/bottom boundary testing
│   ├── test_restack.py      # Restack happy path, conflicts, partial failure
│   ├── test_stack_mgmt.py   # stack new/list/switch/delete
│   ├── test_delete.py       # Delete from top/middle/bottom
│   ├── test_sync.py         # Sync with remote (needs bare repo fixture)
│   ├── test_submit.py       # PR creation (mocked gh CLI)
│   └── test_trunk.py        # Trunk show/set
└── e2e/
    └── test_full_workflow.py # Complete stacking lifecycle
```

---

## Bugs to Fix

### Critical (data corruption/loss risk)
| # | Bug | File | Fix |
|---|-----|------|-----|
| 1 | Non-atomic state writes — crash mid-write corrupts state.json | `store.py` | Write to temp file + `os.replace()` atomic rename |
| 2 | No state validation on load — missing keys cause KeyError | `store.py` | Add schema validation with defaults for missing fields |
| 3 | Force-push without divergence check — silently overwrites collaborator commits | `submit.py` | Add `--force` flag requirement or divergence detection |

### High (broken functionality)
| # | Bug | File | Fix |
|---|-----|------|-----|
| 4 | Navigation from trunk goes to top instead of bottom+1 | `navigate.py:20` | `up` from trunk should go to `branches[0]` |
| 5 | Stash pop on rebased branch may conflict | `restack.py:109` | Warn user; pop stash only if working tree is compatible |
| 6 | No dirty working tree check before navigate/switch | `navigate.py`, `stack.py` | Add `is_working_tree_clean()` check with helpful error |
| 7 | `sync.py` fails when already on trunk | `sync.py:21` | Detect trunk state and skip redundant checkout |
| 8 | `ValueError` crash on `gs up abc` | `navigate.py:30` | Validate arg is numeric |

### Medium (incorrect output/state)
| # | Bug | File | Fix |
|---|-----|------|-----|
| 9 | "Moved to: parent" printed even when no move occurred | `delete.py:51` | Conditional print |
| 10 | `create_pr` returns PrInfo with number=0 | `github.py:103` | Raise error instead of returning invalid data |
| 11 | Trunk command doesn't update existing stacks | `trunk.py:22` | Offer to update stacks referencing old trunk |
| 12 | Partial state save on restack failure | `restack.py:96` | Only save state for successfully restacked branches |

---

## Missing Requirements for Daily SWE Workflow

### Must-Have (P0)
1. **`gs diff`** — Show diff of current branch vs its parent (not vs HEAD~1). Essential for reviewing what THIS branch adds.
2. **`gs restack --continue`** — After resolving conflicts, continue restacking remaining branches without re-doing completed ones.
3. **Detached HEAD detection** — Detect and error gracefully instead of cryptic failures.
4. **Branch-deleted-externally detection** — If a branch in the stack was deleted outside gitstacker, detect and offer to clean up.
5. **Atomic state persistence** — Prevent corruption on crash/kill.

### Should-Have (P1)
6. **`gs land`** — After bottom PR is merged, remove it from stack and update next branch's base to trunk.
7. **`gs web`** — Open current branch's PR in browser.
8. **Dirty tree handling everywhere** — Stash/error on navigate, switch, sync (not just restack).
9. **State backup/recovery** — Keep last-known-good state copy.
10. **Custom PR titles on submit** — Don't overwrite user-edited titles.

### Nice-to-Have (P2)
11. **`gs absorb`** — Distribute staged hunks to the correct branch in the stack.
12. **`gs insert`** — Insert a branch between two existing stack branches.
13. **PR status in `gs log`** — Show merged/approved/CI status.
14. **`gs submit --branch <name>`** — Submit a single branch instead of entire stack.
15. **Config file support** — `.gitstackerrc` for defaults (draft mode, trunk name, force-push policy).

---

## Test Plan

### Phase 1: Foundation (test infrastructure + unit tests)
- Set up pytest, conftest.py with shared fixtures
- Unit test `store.py` (CRUD, validation, corruption recovery)
- Unit test `git_ops.py` (command construction, error handling)
- Unit test `output.py` (color formatting)
- Unit test `github.py` (body generation, command construction)

### Phase 2: Integration tests (real git repos)
- Test `gs init` in fresh repo, already-initialized repo, non-git directory
- Test `gs create` at various positions (first branch, mid-stack, from trunk)
- Test `gs navigate` at all boundaries (top, bottom, trunk, invalid args)
- Test `gs restack` happy path (3+ branches, trunk advanced)
- Test `gs restack` conflict path (verify clean abort and state recovery)
- Test `gs delete` from top, middle, bottom of stack
- Test `gs stack` management (new, list, switch, delete, multiple stacks)
- Test `gs trunk` show and set

### Phase 3: Edge case & error tests
- Detached HEAD scenarios
- Branch deleted outside gitstacker
- Corrupt/missing state.json recovery
- Concurrent state modification
- Empty branches (no commits above parent)
- Branches with slash names (`feat/auth`)
- Very deep stacks (10+ branches)

### Phase 4: E2E workflow tests
- Full lifecycle: init → stack → create 3 branches → commit → restack → verify history
- Multi-stack workflow: create 2 stacks, switch between them, restack independently
- Simulate upstream: advance trunk, sync, verify all branches updated
- Submit flow (with mocked `gh`): verify correct PR base targeting

---

## Acceptance Criteria

1. **All unit tests pass** — `pytest tests/unit/ -v` exits 0
2. **All integration tests pass** — `pytest tests/integration/ -v` exits 0
3. **E2E workflow tests pass** — `pytest tests/e2e/ -v` exits 0
4. **Coverage > 80%** for core modules (`store.py`, `git_ops.py`, `restack.py`, `navigate.py`)
5. **Critical bugs fixed** — Atomic writes, state validation, navigation from trunk
6. **No test requires network** — `gh` CLI is mocked in submit tests
7. **Tests run in < 30 seconds** total
8. **`gs diff` command implemented and tested**
9. **`gs restack --continue` implemented and tested**
10. **All commands handle dirty working tree gracefully**

---

## Implementation Order

1. Fix critical bugs (atomic writes, state validation) — foundation for reliable tests
2. Set up test infrastructure (pytest, fixtures, conftest.py)
3. Write unit tests for store.py and git_ops.py
4. Write integration tests for each command
5. Fix remaining bugs as tests expose them
6. Implement `gs diff` + tests
7. Implement `gs restack --continue` + tests
8. Add dirty working tree handling everywhere + tests
9. Write E2E workflow tests
10. Implement P1 features (land, web) if time permits
