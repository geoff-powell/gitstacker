"""Shell alias generation for gitstacker.

Generates shell aliases that provide short terminal commands for all gs operations.
Usage: gs aliases [bash|zsh|fish]
       eval "$(gs aliases)"        # Add to shell rc file
"""

# Alias definitions: (alias_name, gs_command, description)
ALIASES = [
    ("gsc", "gs create", "Create a new branch on the current stack"),
    ("gss", "gs stack", "Stack management commands"),
    ("gsu", "gs up", "Move up in the stack"),
    ("gsd", "gs down", "Move down in the stack"),
    ("gsl", "gs log", "Show the current stack"),
    ("gsm", "gs modify", "Amend/commit and auto-restack upstack"),
    ("gsrs", "gs restack", "Rebase all branches in current stack"),
    ("gspr", "gs submit", "Create/update stacked PRs"),
    ("gsrm", "gs delete", "Remove branch from stack"),
    ("gsbot", "gs bottom", "Jump to bottom of stack"),
    ("gstop", "gs top", "Jump to top of stack"),
    ("gssync", "gs sync", "Fetch trunk, update, and restack"),
    ("gsdiff", "gs diff", "Show diff of current branch vs parent"),
    ("gsst", "gs status", "Show current state"),
]


def _bash_aliases() -> str:
    """Generate bash/zsh alias definitions."""
    lines = [
        "# GitStacker shell aliases",
        "# Add to ~/.bashrc or ~/.zshrc:",
        '#   eval "$(gs aliases)"',
        "",
    ]
    for alias, command, desc in ALIASES:
        lines.append(f"alias {alias}='{command}'  # {desc}")
    return "\n".join(lines) + "\n"


def _fish_aliases() -> str:
    """Generate fish shell abbreviations."""
    lines = [
        "# GitStacker shell abbreviations for fish",
        "# Add to ~/.config/fish/config.fish:",
        "#   gs aliases fish | source",
        "",
    ]
    for alias, command, desc in ALIASES:
        lines.append(f"# {desc}")
        lines.append(f"abbr -a {alias} {command}")
    return "\n".join(lines) + "\n"


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

    if shell in ("bash", "zsh"):
        print(_bash_aliases())
    elif shell == "fish":
        print(_fish_aliases())
    elif shell == "--list":
        # Machine-readable list for scripts/AI
        for alias, command, desc in ALIASES:
            print(f"{alias:8s} → {command:15s}  {desc}")
    else:
        print(f"Unsupported shell: {shell}")
        print("Supported: bash, zsh, fish")
        print("Use --list to see all aliases")
        raise SystemExit(1)
