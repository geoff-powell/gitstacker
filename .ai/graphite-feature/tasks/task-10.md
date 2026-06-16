# Task 10: Integration Tests for Stack Management

## Description
Write integration tests for stack management commands (`gs stack new/list/switch/delete`) and the `gs delete` branch command. Also verify the delete bug fix (Bug #9: "Moved to: parent" printed even when no move occurred).

## Files to Create/Modify
- `tests/integration/test_stack_mgmt.py` — Tests for stack new/list/switch/delete
- `tests/integration/test_delete.py` — Tests for branch deletion from stack
- `tests/integration/test_trunk.py` — Tests for trunk show/set
- `gitstacker/commands/delete.py` — Fix Bug #9 (conditional "Moved to" print)

## Implementation Details

### Fix Bug #9 in delete.py
The line `info(f"Moved to: {parent}")` at line 51 prints even when the user wasn't on the deleted branch:

```python
# CURRENT (always prints):
info(f"Moved to: {parent}")

# FIXED (conditional):
if current_branch == branch:
    info(f"Moved to: {parent}")
```

### test_stack_mgmt.py

```python
import pytest
from gitstacker.commands.stack import cmd_stack
from gitstacker.commands.create import cmd_create
from gitstacker.store import load_state
from gitstacker.git_ops import get_current_branch, checkout


class TestStackNew:
    def test_create_stack(self, initialized_repo):
        cmd_stack(["new", "my-stack"])
        state = load_state()
        assert "my-stack" in state["stacks"]
        assert state["current_stack"] == "my-stack"

    def test_create_duplicate_errors(self, initialized_repo):
        cmd_stack(["new", "s"])
        with pytest.raises(SystemExit):
            cmd_stack(["new", "s"])

    def test_create_no_name_errors(self, initialized_repo):
        with pytest.raises(SystemExit):
            cmd_stack(["new"])


class TestStackList:
    def test_list_empty(self, initialized_repo, capsys):
        cmd_stack(["list"])
        captured = capsys.readouterr()
        assert "no stacks" in captured.out.lower()

    def test_list_shows_stacks(self, initialized_repo, capsys):
        cmd_stack(["new", "stack-a"])
        cmd_stack(["new", "stack-b"])
        cmd_stack(["list"])
        captured = capsys.readouterr()
        assert "stack-a" in captured.out
        assert "stack-b" in captured.out

    def test_list_shows_active(self, stacked_repo, capsys):
        checkout("branch-1")
        cmd_stack(["list"])
        captured = capsys.readouterr()
        assert "active" in captured.out.lower()


class TestStackSwitch:
    def test_switch_to_existing(self, initialized_repo):
        cmd_stack(["new", "stack-a"])
        cmd_create(["br-a"])
        cmd_stack(["new", "stack-b"])
        cmd_create(["br-b"])
        cmd_stack(["switch", "stack-a"])
        state = load_state()
        assert state["current_stack"] == "stack-a"
        assert get_current_branch() == "br-a"

    def test_switch_nonexistent_errors(self, initialized_repo):
        with pytest.raises(SystemExit):
            cmd_stack(["switch", "nope"])

    def test_switch_no_name_errors(self, initialized_repo):
        with pytest.raises(SystemExit):
            cmd_stack(["switch"])


class TestStackDelete:
    def test_delete_stack(self, initialized_repo):
        cmd_stack(["new", "to-delete"])
        cmd_stack(["delete", "to-delete"])
        state = load_state()
        assert "to-delete" not in state["stacks"]

    def test_delete_clears_current_stack(self, initialized_repo):
        cmd_stack(["new", "only-stack"])
        cmd_stack(["delete", "only-stack"])
        state = load_state()
        assert state["current_stack"] is None

    def test_delete_nonexistent_errors(self, initialized_repo):
        with pytest.raises(SystemExit):
            cmd_stack(["delete", "ghost"])
```

### test_delete.py

```python
import pytest
from gitstacker.commands.delete import cmd_delete
from gitstacker.commands.create import cmd_create
from gitstacker.commands.stack import cmd_stack
from gitstacker.store import load_state
from gitstacker.git_ops import get_current_branch, checkout


class TestDeleteBranch:
    def test_delete_top_branch(self, stacked_repo):
        checkout("branch-3")
        cmd_delete([])
        state = load_state()
        assert "branch-3" not in state["stacks"]["test-stack"]["branches"]
        assert get_current_branch() != "branch-3"

    def test_delete_middle_reparents_child(self, stacked_repo):
        checkout("branch-2")
        cmd_delete([])
        state = load_state()
        assert state["branches"]["branch-3"]["parent"] == "branch-1"

    def test_delete_bottom_reparents_to_trunk(self, stacked_repo):
        checkout("branch-1")
        cmd_delete([])
        state = load_state()
        assert state["branches"]["branch-2"]["parent"] == "main"

    def test_delete_by_name(self, stacked_repo):
        checkout("main")
        cmd_delete(["branch-2"])
        state = load_state()
        assert "branch-2" not in state["stacks"]["test-stack"]["branches"]

    def test_delete_non_stacked_errors(self, stacked_repo):
        with pytest.raises(SystemExit):
            cmd_delete(["nonexistent"])

    def test_delete_with_force_removes_git_branch(self, stacked_repo):
        checkout("main")
        cmd_delete(["branch-3", "--force"])
        from gitstacker.git_ops import branch_exists
        assert not branch_exists("branch-3")

    def test_delete_no_move_message_when_not_on_branch(self, stacked_repo, capsys):
        """Bug #9: Don't print 'Moved to' when not on the deleted branch."""
        checkout("main")
        cmd_delete(["branch-3"])
        captured = capsys.readouterr()
        assert "moved to" not in captured.out.lower()
```

### test_trunk.py

```python
import pytest
import subprocess
from gitstacker.commands.trunk import cmd_trunk
from gitstacker.store import load_state


class TestTrunk:
    def test_show_trunk(self, initialized_repo, capsys):
        cmd_trunk([])
        captured = capsys.readouterr()
        assert "main" in captured.out

    def test_set_trunk(self, initialized_repo):
        subprocess.run(["git", "branch", "develop"], cwd=initialized_repo, check=True)
        cmd_trunk(["develop"])
        state = load_state()
        assert state["trunk"] == "develop"

    def test_set_nonexistent_errors(self, initialized_repo):
        with pytest.raises(SystemExit):
            cmd_trunk(["nonexistent"])

    def test_set_trunk_updates_stacks(self, stacked_repo):
        """Bug #11: Setting trunk updates stacks referencing old trunk."""
        subprocess.run(["git", "branch", "develop"], cwd=stacked_repo, check=True)
        cmd_trunk(["develop"])
        state = load_state()
        assert state["stacks"]["test-stack"]["trunk"] == "develop"
```

## Dependencies
- Depends on: task-02 (test infrastructure), task-05 (trunk bug fix)

## Acceptance Criteria
- [ ] `pytest tests/integration/test_stack_mgmt.py tests/integration/test_delete.py tests/integration/test_trunk.py -v` passes
- [ ] Stack new/list/switch/delete all tested
- [ ] Branch delete from top/middle/bottom tested with proper reparenting
- [ ] Bug #9 fixed: "Moved to" only printed when actually moved
- [ ] Bug #11 verified: trunk set updates existing stacks
- [ ] Force delete removes git branch
- [ ] Error cases tested for all commands
- [ ] At least 20 test cases total

## Notes
- The `stacked_repo` fixture provides `test-stack` with branches `branch-1`, `branch-2`, `branch-3`.
- Delete from middle is the most complex case — verify the child's parent pointer is updated.
- Use `capsys` to verify output messages (especially Bug #9 fix).
