"""Integration tests for gs submit — mocked gh CLI, no network required."""

import pytest
from unittest.mock import patch, MagicMock
from gitstacker.commands.submit import cmd_submit
from gitstacker.commands.create import cmd_create
from gitstacker.commands.stack import cmd_stack
from gitstacker.git_ops import checkout
from gitstacker.store import load_state
from gitstacker.github import PrInfo, GhResult
import subprocess


def add_commit(repo, filename, content, message):
    (repo / filename).write_text(content)
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", message], cwd=repo, check=True)


class TestSubmitMocked:
    """Tests with mocked gh CLI — no network required."""

    @patch("gitstacker.commands.submit.is_gh_available", return_value=True)
    @patch("gitstacker.commands.submit.get_pr_for_branch", return_value=None)
    @patch("gitstacker.commands.submit.create_pr")
    @patch("gitstacker.commands.submit.push_branch")
    @patch("gitstacker.commands.submit.has_remote_diverged", return_value=False)
    def test_submit_creates_prs(
        self, mock_diverged, mock_push, mock_create, mock_get_pr, mock_gh, initialized_repo
    ):
        """Submit creates PRs for all branches."""
        cmd_stack(["new", "s"])
        cmd_create(["b1"])
        add_commit(initialized_repo, "f.txt", "x", "commit")

        mock_push.return_value = MagicMock(success=True)
        mock_create.return_value = PrInfo(
            number=1, url="https://github.com/org/repo/pull/1",
            title="B1", state="OPEN", base="main", head="b1"
        )

        cmd_submit([])
        mock_create.assert_called_once()

    @patch("gitstacker.commands.submit.is_gh_available", return_value=False)
    def test_submit_no_gh_errors(self, mock_gh, initialized_repo):
        """Submit without gh CLI errors."""
        with pytest.raises(SystemExit):
            cmd_submit([])

    @patch("gitstacker.commands.submit.is_gh_available", return_value=True)
    @patch("gitstacker.commands.submit.get_pr_for_branch")
    @patch("gitstacker.commands.submit.update_pr_base")
    @patch("gitstacker.commands.submit.update_pr")
    @patch("gitstacker.commands.submit.push_branch")
    @patch("gitstacker.commands.submit.has_remote_diverged", return_value=False)
    def test_submit_updates_existing_pr_base(
        self, mock_diverged, mock_push, mock_update, mock_update_base, mock_get_pr, mock_gh, initialized_repo
    ):
        """Submit updates PR base when parent changed."""
        cmd_stack(["new", "s"])
        cmd_create(["b1"])
        add_commit(initialized_repo, "f.txt", "x", "commit")

        mock_push.return_value = MagicMock(success=True)
        mock_get_pr.return_value = PrInfo(
            number=42, url="https://github.com/org/repo/pull/42",
            title="B1", state="OPEN", base="old-parent", head="b1"
        )

        cmd_submit([])
        mock_update_base.assert_called_once_with(42, "main")

    @patch("gitstacker.commands.submit.is_gh_available", return_value=True)
    @patch("gitstacker.commands.submit.push_branch")
    @patch("gitstacker.commands.submit.has_remote_diverged", return_value=False)
    @patch("gitstacker.commands.submit.get_pr_for_branch", return_value=None)
    @patch("gitstacker.commands.submit.create_pr")
    def test_submit_draft_flag(
        self, mock_create, mock_get_pr, mock_diverged, mock_push, mock_gh, initialized_repo
    ):
        """--draft flag is passed to create_pr."""
        cmd_stack(["new", "s"])
        cmd_create(["b1"])
        add_commit(initialized_repo, "f.txt", "x", "commit")

        mock_push.return_value = MagicMock(success=True)
        mock_create.return_value = PrInfo(
            number=1, url="url", title="B1", state="OPEN", base="main", head="b1"
        )

        cmd_submit(["--draft"])
        _, kwargs = mock_create.call_args
        assert kwargs.get("draft") is True

    @patch("gitstacker.commands.submit.is_gh_available", return_value=True)
    @patch("gitstacker.commands.submit.push_branch")
    @patch("gitstacker.commands.submit.has_remote_diverged", return_value=True)
    @patch("gitstacker.commands.submit.get_pr_for_branch", return_value=None)
    @patch("gitstacker.commands.submit.create_pr")
    def test_submit_diverged_skips_push(
        self, mock_create, mock_get_pr, mock_diverged, mock_push, mock_gh, initialized_repo
    ):
        """When remote has diverged and no --force, push is skipped."""
        cmd_stack(["new", "s"])
        cmd_create(["b1"])
        add_commit(initialized_repo, "f.txt", "x", "commit")

        mock_push.return_value = MagicMock(success=True)
        mock_create.return_value = PrInfo(
            number=1, url="url", title="B1", state="OPEN", base="main", head="b1"
        )

        cmd_submit([])
        # push_branch should NOT have been called since diverged without --force
        mock_push.assert_not_called()

    @patch("gitstacker.commands.submit.is_gh_available", return_value=True)
    @patch("gitstacker.commands.submit.push_branch")
    @patch("gitstacker.commands.submit.has_remote_diverged", return_value=True)
    @patch("gitstacker.commands.submit.get_pr_for_branch", return_value=None)
    @patch("gitstacker.commands.submit.create_pr")
    def test_submit_diverged_with_force_pushes(
        self, mock_create, mock_get_pr, mock_diverged, mock_push, mock_gh, initialized_repo
    ):
        """When remote diverged but --force is used, push proceeds."""
        cmd_stack(["new", "s"])
        cmd_create(["b1"])
        add_commit(initialized_repo, "f.txt", "x", "commit")

        mock_push.return_value = MagicMock(success=True)
        mock_create.return_value = PrInfo(
            number=1, url="url", title="B1", state="OPEN", base="main", head="b1"
        )

        cmd_submit(["--force"])
        # push_branch SHOULD be called since --force overrides divergence
        mock_push.assert_called_once()


class TestCreatePrValidation:
    """Tests for Bug #10 fix."""

    @patch("gitstacker.github.gh")
    @patch("gitstacker.github.get_pr_for_branch", return_value=None)
    def test_create_pr_raises_on_unparseable_url(self, mock_get, mock_gh):
        """create_pr raises instead of returning number=0."""
        from gitstacker.github import create_pr
        mock_gh.return_value = GhResult(
            stdout="some-garbage-not-a-url", stderr="", returncode=0
        )
        with pytest.raises(RuntimeError, match="could not determine PR number"):
            create_pr(title="T", body="B", base="main", head="b1")

    @patch("gitstacker.github.gh")
    @patch("gitstacker.github.get_pr_for_branch", return_value=None)
    def test_create_pr_parses_url_correctly(self, mock_get, mock_gh):
        """create_pr extracts number from valid URL."""
        from gitstacker.github import create_pr
        mock_gh.return_value = GhResult(
            stdout="https://github.com/org/repo/pull/99", stderr="", returncode=0
        )
        pr = create_pr(title="T", body="B", base="main", head="b1")
        assert pr.number == 99
