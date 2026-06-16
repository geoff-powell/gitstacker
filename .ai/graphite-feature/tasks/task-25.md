# Task 25: Wire Up CLI Dispatch, Help Text, and Shell Completions

## Description
Add dispatch entries for all new commands (`modify`, `undo`, `get`, `freeze`, `unfreeze`) to `cli.py`, update the help text, and extend shell completions.

## Dependencies
- Task 19 (undo.py exists)
- Task 22 (freeze.py exists)
- Task 23 (modify.py exists)
- Task 24 (get.py exists)

## Affected Files
- `gitstacker/cli.py` — add dispatch entries + update HELP_TEXT
- `gitstacker/commands/completions.py` — add new commands to all three shells

## Implementation Details

### Modify `gitstacker/cli.py`

#### 1. Update the module docstring (top of file) to include new commands:

Add these lines to the docstring command list:
```
  modify              Amend/commit and auto-restack
  undo                Undo the last operation
  get <branch>        Fetch and discover a remote stack
  freeze [branch]     Freeze a branch (skip restack/modify)
  unfreeze [branch]   Unfreeze a branch
```

#### 2. Update `HELP_TEXT` string

Add new entries in the COMMANDS section (after the `status` line):

```python
  {cyan("modify")} [--all] [-m msg]  Amend current branch and auto-restack
  {cyan("undo")}                    Undo the last mutating operation
  {cyan("get")} <branch>            Fetch a remote stack
  {cyan("freeze")} [branch]         Freeze branch (skip restack/modify)
  {cyan("unfreeze")} [branch]       Unfreeze a branch
```

Add new aliases to the ALIASES section:
```python
  m     = modify
```

#### 3. Add dispatch entries in `main()`

Add these elif blocks after the `status` dispatch and before the `else` (unknown command) block:

```python
        elif command in ("modify", "m"):
            from .commands.modify import cmd_modify
            cmd_modify(command_args)

        elif command == "undo":
            from .commands.undo import cmd_undo
            cmd_undo(command_args)

        elif command == "get":
            from .commands.get import cmd_get
            cmd_get(command_args)

        elif command == "freeze":
            from .commands.freeze import cmd_freeze
            cmd_freeze(command_args)

        elif command == "unfreeze":
            from .commands.freeze import cmd_unfreeze
            cmd_unfreeze(command_args)
```

### Modify `gitstacker/commands/completions.py`

Add completions for the new commands in all three shell formats.

#### Bash completions
Add to the command list:
```bash
modify undo get freeze unfreeze
```

Add flag completions for modify:
```bash
# modify flags
if [[ "${prev}" == "modify" || "${prev}" == "m" ]]; then
    COMPREPLY=($(compgen -W "--all -a --commit -c --message -m --into --continue" -- "${cur}"))
    return 0
fi
```

#### Zsh completions
Add to the commands array:
```zsh
'modify:Amend/commit and auto-restack upstack'
'undo:Undo the last mutating operation'
'get:Fetch and discover a remote stack'
'freeze:Freeze a branch'
'unfreeze:Unfreeze a branch'
'm:Alias for modify'
```

#### Fish completions
Add:
```fish
complete -c gs -n "__fish_use_subcommand" -a modify -d "Amend/commit and auto-restack"
complete -c gs -n "__fish_use_subcommand" -a undo -d "Undo the last operation"
complete -c gs -n "__fish_use_subcommand" -a get -d "Fetch a remote stack"
complete -c gs -n "__fish_use_subcommand" -a freeze -d "Freeze a branch"
complete -c gs -n "__fish_use_subcommand" -a unfreeze -d "Unfreeze a branch"
complete -c gs -n "__fish_use_subcommand" -a m -d "Alias for modify"

# modify flags
complete -c gs -n "__fish_seen_subcommand_from modify m" -l all -s a -d "Stage all changes"
complete -c gs -n "__fish_seen_subcommand_from modify m" -l commit -s c -d "New commit (don't amend)"
complete -c gs -n "__fish_seen_subcommand_from modify m" -l message -s m -d "Commit message" -r
complete -c gs -n "__fish_seen_subcommand_from modify m" -l into -d "Target branch" -r
complete -c gs -n "__fish_seen_subcommand_from modify m" -l continue -d "Resume after conflict"
```

## Acceptance Criteria
- [ ] `gs modify` dispatches to `cmd_modify`
- [ ] `gs m` dispatches to `cmd_modify` (alias)
- [ ] `gs undo` dispatches to `cmd_undo`
- [ ] `gs get <branch>` dispatches to `cmd_get`
- [ ] `gs freeze` dispatches to `cmd_freeze`
- [ ] `gs unfreeze` dispatches to `cmd_unfreeze`
- [ ] `gs --help` shows all new commands with descriptions
- [ ] `gs completions bash` includes new commands and modify flags
- [ ] `gs completions zsh` includes new commands
- [ ] `gs completions fish` includes new commands and modify flags
- [ ] No unknown command error for any of the new commands
- [ ] Help text formatting is consistent with existing entries
