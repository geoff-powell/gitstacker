"""
Unit tests for gitstacker/github.py — stack comment management functions.
"""

from unittest.mock import patch

import pytest

from gitstacker.github import (
    STACK_COMMENT_MARKER,
    GhResult,
    _create_comment,
    _find_stack_comment,
    _update_comment,
    generate_stack_comment,
    upsert_stack_comment,
)


class TestFindStackComment:
    """Tests for _find_stack_comment() — locating existing stack comments on PRs."""

    @patch("gitstacker.github.gh")
    def test_returns_comment_id_when_marker_found(self, mock_gh):
        """Returns integer comment ID when gh finds a matching comment."""
        mock_gh.return_value = GhResult(stdout="12345", stderr="", returncode=0)

        result = _find_stack_comment(42)

        assert result == 12345
        mock_gh.assert_called_once_with(
            "api", "repos/{owner}/{repo}/issues/42/comments",
            "--paginate",
            "--jq", f'[.[] | select(.body | contains("{STACK_COMMENT_MARKER}"))][0].id',
        )

    @patch("gitstacker.github.gh")
    def test_returns_none_when_gh_call_fails(self, mock_gh):
        """Returns None when gh exits with non-zero returncode."""
        mock_gh.return_value = GhResult(stdout="", stderr="API error", returncode=1)

        result = _find_stack_comment(99)

        assert result is None

    @patch("gitstacker.github.gh")
    def test_returns_none_when_stdout_is_empty(self, mock_gh):
        """Returns None when gh succeeds but stdout is empty (no matching comment)."""
        mock_gh.return_value = GhResult(stdout="", stderr="", returncode=0)

        result = _find_stack_comment(7)

        assert result is None

    @patch("gitstacker.github.gh")
    def test_returns_none_when_stdout_is_whitespace(self, mock_gh):
        """Returns None when gh succeeds but stdout is only whitespace."""
        mock_gh.return_value = GhResult(stdout="   \n  ", stderr="", returncode=0)

        result = _find_stack_comment(7)

        assert result is None

    @patch("gitstacker.github.gh")
    def test_returns_none_when_stdout_is_null(self, mock_gh):
        """Returns None when jq outputs 'null' (no matching comment)."""
        mock_gh.return_value = GhResult(stdout="null", stderr="", returncode=0)

        result = _find_stack_comment(5)

        assert result is None

    @patch("gitstacker.github.gh")
    def test_returns_none_for_non_integer_response(self, mock_gh):
        """Returns None when stdout cannot be parsed as an integer."""
        mock_gh.return_value = GhResult(stdout="not-a-number", stderr="", returncode=0)

        result = _find_stack_comment(10)

        assert result is None


class TestCreateComment:
    """Tests for _create_comment() — creating new PR comments."""

    @patch("gitstacker.github.gh")
    def test_returns_true_on_success(self, mock_gh):
        """Returns True when gh pr comment succeeds."""
        mock_gh.return_value = GhResult(stdout="", stderr="", returncode=0)

        result = _create_comment(42, "Hello, world!")

        assert result is True
        mock_gh.assert_called_once_with("pr", "comment", "42", "--body", "Hello, world!")

    @patch("gitstacker.github.gh")
    def test_returns_false_on_failure(self, mock_gh):
        """Returns False when gh pr comment fails."""
        mock_gh.return_value = GhResult(stdout="", stderr="not found", returncode=1)

        result = _create_comment(999, "body text")

        assert result is False


class TestUpdateComment:
    """Tests for _update_comment() — updating existing comments by ID."""

    @patch("gitstacker.github.gh")
    def test_returns_true_on_success(self, mock_gh):
        """Returns True when API PATCH succeeds."""
        mock_gh.return_value = GhResult(stdout="{}", stderr="", returncode=0)

        result = _update_comment(12345, "Updated body")

        assert result is True
        mock_gh.assert_called_once_with(
            "api", "repos/{owner}/{repo}/issues/comments/12345",
            "-X", "PATCH",
            "-f", "body=Updated body",
        )

    @patch("gitstacker.github.gh")
    def test_returns_false_on_failure(self, mock_gh):
        """Returns False when comment was deleted (404) or API fails."""
        mock_gh.return_value = GhResult(stdout="", stderr="404 Not Found", returncode=1)

        result = _update_comment(99999, "body")

        assert result is False


class TestGenerateStackComment:
    """Tests for generate_stack_comment() — building the markdown comment body."""

    def test_single_branch_stack_contains_branch_and_marker(self):
        """Single-branch stack output contains the branch name and hidden marker."""
        body = generate_stack_comment(
            stack_name="my-stack",
            branches=["feature-1"],
            current_branch="feature-1",
            pr_numbers={"feature-1": 10},
            pr_urls={"feature-1": "https://github.com/org/repo/pull/10"},
        )

        assert "feature-1" in body
        assert STACK_COMMENT_MARKER in body
        assert "my-stack" in body

    def test_multi_branch_marks_current_with_arrow(self):
        """Multi-branch stack marks the current branch with '← this PR'."""
        body = generate_stack_comment(
            stack_name="my-stack",
            branches=["branch-1", "branch-2", "branch-3"],
            current_branch="branch-2",
            pr_numbers={"branch-1": 1, "branch-2": 2, "branch-3": 3},
            pr_urls={
                "branch-1": "https://github.com/org/repo/pull/1",
                "branch-2": "https://github.com/org/repo/pull/2",
                "branch-3": "https://github.com/org/repo/pull/3",
            },
        )

        assert "\u2190 this PR" in body
        # The current branch line should have the arrow marker
        for line in body.splitlines():
            if "branch-2" in line:
                assert "\u2190 this PR" in line
            elif "branch-1" in line or "branch-3" in line:
                assert "\u2190 this PR" not in line

    def test_branches_without_pr_show_no_pr(self):
        """Branches without PR numbers show '_no PR_'."""
        body = generate_stack_comment(
            stack_name="my-stack",
            branches=["branch-1", "branch-2"],
            current_branch="branch-1",
            pr_numbers={"branch-1": 5},
            pr_urls={"branch-1": "https://github.com/org/repo/pull/5"},
        )

        # branch-2 has no PR number, should show "_no PR_"
        for line in body.splitlines():
            if "branch-2" in line:
                assert "_no PR_" in line
                break
        else:
            pytest.fail("branch-2 not found in output")

    def test_branches_with_url_get_markdown_link(self):
        """Branches with a URL get a markdown link [#N](url)."""
        body = generate_stack_comment(
            stack_name="my-stack",
            branches=["feature-1"],
            current_branch="feature-1",
            pr_numbers={"feature-1": 42},
            pr_urls={"feature-1": "https://github.com/org/repo/pull/42"},
        )

        assert "[#42](https://github.com/org/repo/pull/42)" in body

    def test_output_ends_with_stack_comment_marker(self):
        """Generated comment always ends with the STACK_COMMENT_MARKER."""
        body = generate_stack_comment(
            stack_name="test-stack",
            branches=["a", "b", "c"],
            current_branch="b",
            pr_numbers={"a": 1, "b": 2, "c": 3},
            pr_urls={},
        )

        assert body.strip().endswith(STACK_COMMENT_MARKER)

    def test_branches_listed_top_down(self):
        """Branches are listed from top of stack (last) to bottom (first)."""
        body = generate_stack_comment(
            stack_name="my-stack",
            branches=["bottom", "middle", "top"],
            current_branch="middle",
            pr_numbers={},
            pr_urls={},
        )

        lines = body.splitlines()
        top_idx = next(i for i, l in enumerate(lines) if "top" in l)
        middle_idx = next(i for i, l in enumerate(lines) if "middle" in l)
        bottom_idx = next(i for i, l in enumerate(lines) if "bottom" in l)
        # Top of stack appears first in listing
        assert top_idx < middle_idx < bottom_idx


class TestUpsertStackComment:
    """Tests for upsert_stack_comment() — create-or-update logic."""

    @patch("gitstacker.github._create_comment")
    @patch("gitstacker.github._find_stack_comment")
    @patch("gitstacker.github.generate_stack_comment")
    def test_creates_new_comment_when_none_exists(
        self, mock_generate, mock_find, mock_create
    ):
        """Creates a new comment when no existing stack comment is found."""
        mock_generate.return_value = "generated body"
        mock_find.return_value = None
        mock_create.return_value = True

        result = upsert_stack_comment(
            pr_number=10,
            stack_name="my-stack",
            branches=["b1", "b2"],
            current_branch="b1",
            pr_numbers={"b1": 10, "b2": 11},
            pr_urls={"b1": "url1", "b2": "url2"},
        )

        assert result is True
        mock_find.assert_called_once_with(10)
        mock_create.assert_called_once_with(10, "generated body")

    @patch("gitstacker.github._update_comment")
    @patch("gitstacker.github._find_stack_comment")
    @patch("gitstacker.github.generate_stack_comment")
    def test_updates_existing_comment_when_found(
        self, mock_generate, mock_find, mock_update
    ):
        """Updates the existing comment when one is found."""
        mock_generate.return_value = "updated body"
        mock_find.return_value = 555
        mock_update.return_value = True

        result = upsert_stack_comment(
            pr_number=10,
            stack_name="my-stack",
            branches=["b1"],
            current_branch="b1",
            pr_numbers={"b1": 10},
            pr_urls={"b1": "url1"},
        )

        assert result is True
        mock_find.assert_called_once_with(10)
        mock_update.assert_called_once_with(555, "updated body")

    @patch("gitstacker.github._create_comment")
    @patch("gitstacker.github._update_comment")
    @patch("gitstacker.github._find_stack_comment")
    @patch("gitstacker.github.generate_stack_comment")
    def test_falls_through_to_create_when_update_fails(
        self, mock_generate, mock_find, mock_update, mock_create
    ):
        """Falls through to create when update fails (TOCTOU race: comment deleted)."""
        mock_generate.return_value = "body text"
        mock_find.return_value = 777
        mock_update.return_value = False  # Simulate deleted comment
        mock_create.return_value = True

        result = upsert_stack_comment(
            pr_number=10,
            stack_name="my-stack",
            branches=["b1"],
            current_branch="b1",
            pr_numbers={"b1": 10},
            pr_urls={"b1": "url1"},
        )

        assert result is True
        mock_update.assert_called_once_with(777, "body text")
        mock_create.assert_called_once_with(10, "body text")
