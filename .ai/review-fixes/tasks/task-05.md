# Task 05: Handle --help Flag in Aliases Command

## Summary
Add proper `--help` / `-h` handling to `cmd_aliases()` so it prints usage information instead of the confusing "Unsupported shell: --help" error.

## Files to Modify
- `gitstacker/commands/aliases.py`

## Implementation Details

Add a check at the top of `cmd_aliases()`:

```python
def cmd_aliases(args: list[str]) -> None:
    """Output shell aliases for gs commands."""
    shell = args[0] if args else "bash"

    if shell in ("--help", "-h"):
        print("Usage: gs aliases [bash|zsh|fish|--list]")
        print()
        print("Generate shell aliases for gitstacker commands.")
        print()
        print("Shells:")
        print("  bash, zsh   Alias definitions (eval-able)")
        print("  fish        Fish abbreviations (source-able)")
        print("  --list      Machine-readable alias list")
        print()
        print("Examples:")
        print('  eval "$(gs aliases)"              # bash/zsh')
        print("  gs aliases fish | source          # fish")
        return

    # ... rest of function unchanged
```

## Acceptance Criteria
- [ ] `gs aliases --help` prints usage info and exits cleanly
- [ ] `gs aliases -h` also prints usage info
- [ ] Existing behavior for bash/zsh/fish/--list is unchanged
