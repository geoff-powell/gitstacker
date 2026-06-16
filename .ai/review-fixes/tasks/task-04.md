# Task 04: Unit Tests for Comment Functions

## Summary
Add comprehensive unit tests for the stack comment functions in `github.py`:
- `_find_stack_comment`
- `_create_comment`
- `_update_comment`
- `generate_stack_comment`
- `upsert_stack_comment` (including the retry-create fallback)

## Files to Create
- `tests/unit/test_github_comments.py`

## Implementation Details

Test cases to cover:

### `_find_stack_comment`
- Returns comment ID when marker comment exists
- Returns None when no comments match
- Returns None when API call fails
- Returns None when response is "null" (empty results)
- Handles non-integer response gracefully

### `_create_comment`
- Returns True on success
- Returns False on failure

### `_update_comment`
- Returns True on success
- Returns False on failure (404, comment deleted)

### `generate_stack_comment`
- Single branch stack generates correct markdown
- Multi-branch stack with current marker
- Branches without PR numbers show "_no PR_"
- Contains the hidden marker at the end

### `upsert_stack_comment`
- Creates comment when none exists
- Updates existing comment when found
- Falls through to create when update fails (TOCTOU race)

All tests should mock `gitstacker.github.gh` to avoid network calls.

## Acceptance Criteria
- [ ] All comment functions have test coverage
- [ ] Tests mock the `gh` function, no network required
- [ ] TOCTOU retry path is explicitly tested
- [ ] All tests pass
