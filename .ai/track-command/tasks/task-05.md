# Task 05: Update CLI, Help, Aliases, and Completions

## Summary
Register the new `gs track` command in the CLI dispatcher, update help text to reflect the new workflow, and add aliases/completions.

## Files to Modify
- `gitstacker/cli.py` — register command, update help text and examples
- `gitstacker/commands/aliases.py` — add `gstr` alias for `gs track`
- `gitstacker/commands/completions.py` — add `track` to completions

## CLI Registration (cli.py)

Add to the command dispatch:
```python
elif command in ("track", "t"):
    from .commands.track import cmd_track
    cmd_track(command_args)
```

## Help Text Updates

1. Add `track` command to the COMMANDS section:
```
track [branch]          Track existing branch into current stack
```

2. Update EXAMPLES to show the new workflow:
```
# Start a new feature stack
gs init
gs stack new auth-feature
git checkout -b auth-api
# ... make commits ...
gs track
git checkout -b auth-ui
# ... make commits ...
gs track
```

3. Add `t = track` to the ALIASES section

4. Mark `create` as deprecated in help:
```
create <name>           [deprecated] Create branch (use: git checkout -b + gs track)
```

## Aliases (aliases.py)

Add to ALIASES list:
```python
("gstr", "gs track", "Track current branch into stack"),
```

## Completions (completions.py)

Add "track" to the list of commands for shell completion.

## Acceptance Criteria
- [ ] `gs track` dispatches to cmd_track
- [ ] `gs t` also works (short alias)
- [ ] Help text shows track as primary, create as deprecated
- [ ] Examples use the new workflow
- [ ] `gstr` terminal alias works
- [ ] Shell completions include `track`
