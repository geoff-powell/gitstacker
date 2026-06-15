# Plan: Fix Edge Cases from Principal Engineer Review

## Overview

Address 7 edge cases and robustness issues identified during a principal engineer code review of the stack comment feature (`gs submit` PR navigation comments) and shell aliases (`gs aliases`).

## Architecture

No architectural changes required. All fixes are localized to:
- `gitstacker/github.py` — Comment find/create/update logic
- `gitstacker/commands/submit.py` — PR submission orchestration
- `gitstacker/commands/aliases.py` — Shell alias generation
- `tests/` — New unit tests for comment functions

## Stacks (Parallel Workstreams)

### Stack 1: `fix-submit-comments` (sequential dependencies)
Fixes to the PR submission and stack comment system. These all touch `github.py` and `submit.py` so they must be sequential.

- **Task 01**: Seed `pr_numbers` from saved state before the PR creation loop
- **Task 02**: Add retry-create fallback when `_update_comment` fails (TOCTOU fix)
- **Task 03**: Update/remove stale comments when stack shrinks to 1 PR
- **Task 04**: Add unit tests for all comment functions

### Stack 2: `fix-aliases` (sequential dependencies within, but independent of Stack 1)
Fixes to the shell alias command. All in `aliases.py`.

- **Task 05**: Handle `--help`/`-h` flag properly
- **Task 06**: Rename `gst` to `gstop` to avoid conflicts
- **Task 07**: Fix fish `abbr` syntax (comments on separate lines)

## Acceptance Criteria

1. `pr_numbers` dict is pre-seeded from `state["branches"]` so network failures don't lose existing PR references
2. If `_update_comment` fails (404), the function falls through to `_create_comment` instead of silently failing
3. Stack navigation comments are updated even for 1-PR stacks (showing single-PR state) and stale data is corrected
4. `gs aliases --help` prints usage instead of "Unsupported shell: --help"
5. The `gst` alias is renamed to `gstop` to avoid shell conflicts
6. Fish shell abbreviations don't include comment text in the abbreviation
7. All new logic has unit test coverage
8. All 172+ existing tests continue to pass

## Affected Files

| File | Changes |
|------|---------|
| `gitstacker/github.py` | Retry logic in `upsert_stack_comment` |
| `gitstacker/commands/submit.py` | Seed `pr_numbers`, adjust comment threshold |
| `gitstacker/commands/aliases.py` | Help flag, rename alias, fish syntax |
| `tests/unit/test_github_comments.py` | **NEW** — unit tests for comment functions |
| `tests/integration/test_submit.py` | Add test for multi-branch comment flow |

## Non-Goals

- No changes to the PR body generation (`generate_stack_body`)
- No changes to the core git operations or stack state model
- No changes to other commands
