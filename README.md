# GitStacker

**Git branch stacking tool** — manage, rebase, and submit stacked PRs from the command line.

GitStacker (`gs`) lets you work with chains of dependent branches (stacks) where each branch builds on the previous one. It automates rebasing, navigation, conflict resolution, and GitHub PR creation with correct base targeting.

```
main (trunk)
  └── auth-api           (PR #1, base: main)
      └── auth-middleware (PR #2, base: auth-api)
          └── auth-ui    (PR #3, base: auth-middleware)
```

## Why Stacked PRs?

- **Smaller, focused PRs** that are easier to review
- **Ship incrementally** without waiting for a monolithic PR to land
- **Stay unblocked** — start the next piece of work while the previous is in review
- **Auto-generated navigation** — each PR links to the full stack for reviewer context

## Installation

Requires **Python 3.9+** and **Git**. For PR submission, also requires [GitHub CLI (`gh`)](https://cli.github.com).

```bash
# Clone and install in development mode
git clone https://github.com/geoff-powell/gitstacker.git
cd gitstacker
pip install -e .

# Verify
gs --version
```

## Quick Start

```bash
# Initialize in any git repo
gs init

# Create a named stack
gs stack new my-feature

# Create branches (each builds on the previous)
gs create data-layer
# ... make commits ...

gs create business-logic
# ... make commits ...

gs create ui-screen
# ... make commits ...

# View your stack
gs log

# Submit all PRs at once (pushes + creates/updates PRs)
gs submit
```

## Commands

### Stack Management

| Command | Alias | Description |
|---------|-------|-------------|
| `gs stack new <name>` | `gs s <name>` | Create a new named stack |
| `gs stack list` | `gs s` | List all stacks with branch counts |
| `gs stack switch <name>` | `gs s sw <name>` | Switch to a stack |
| `gs stack delete <name>` | `gs s rm <name>` | Delete stack metadata |

### Branch Operations

| Command | Alias | Description |
|---------|-------|-------------|
| `gs create <name>` | `gs c <name>` | Create branch on current stack |
| `gs delete [name] [--force]` | `gs rm` | Remove branch from stack |
| `gs freeze [name]` | — | Skip branch during restack |
| `gs unfreeze [name]` | — | Resume restacking a branch |

### Navigation

| Command | Alias | Description |
|---------|-------|-------------|
| `gs up [n]` | `gs u [n]` | Move up n branches |
| `gs down [n]` | `gs d [n]` | Move down n branches |
| `gs top` | — | Jump to top of stack |
| `gs bottom` | `gs bot` | Jump to bottom of stack |

### Syncing & Rebasing

| Command | Alias | Description |
|---------|-------|-------------|
| `gs restack` | `gs rs` | Rebase all branches in stack |
| `gs sync` | — | Fetch trunk + update + restack |
| `gs modify` | `gs m` | Amend/commit + auto-restack upstack |
| `gs modify --into <branch>` | — | Modify a branch without navigating to it |

### Viewing State

| Command | Alias | Description |
|---------|-------|-------------|
| `gs log [--all]` | `gs l` | Show current stack visually |
| `gs status [--json]` | — | Show current state |
| `gs diff [--stat]` | — | Diff current branch vs parent |

### Submitting PRs

| Command | Alias | Description |
|---------|-------|-------------|
| `gs submit` | `gs pr` | Push all branches + create/update PRs |
| `gs submit --draft` | `gs pr -d` | Create PRs as drafts |
| `gs submit --force` | `gs pr --force` | Force push even if remote diverged |

### Utilities

| Command | Description |
|---------|-------------|
| `gs undo` | Revert last mutating operation |
| `gs trunk [name]` | Show or set trunk branch |
| `gs completions <shell>` | Output shell completions |
| `gs aliases [shell]` | Output terminal aliases |

## Shell Aliases

Install short aliases for faster usage:

```bash
# bash/zsh — add to your rc file
eval "$(gs aliases)"

# fish
gs aliases fish | source
```

This gives you shortcuts like `gsc` (create), `gsu` (up), `gsd` (down), `gsl` (log), `gsm` (modify), `gspr` (submit), etc. Run `gs aliases --list` to see all.

## Workflows

### Modify a Branch Mid-Stack

```bash
# Navigate to the branch
gs down 2

# Make changes, then amend + auto-restack everything above
gs modify -a

# Or add a new commit instead of amending
gs modify -a -c -m "fix: handle edge case"

# Or modify without navigating (stays on current branch)
gs modify --into data-layer -a -c -m "fix: add validation"
```

### Sync with Trunk

```bash
gs sync
# Fetches origin, pulls trunk with rebase, restacks all branches
```

### Handle Rebase Conflicts

```bash
# 1. GitStacker tells you which branch conflicted
# 2. Resolve conflicts in your editor
# 3. Stage and continue
git add .
git rebase --continue
gs restack --continue
```

### Undo a Mistake

```bash
gs undo    # Reverts the last mutating operation
gs undo    # Undo the undo (journal is circular)
```

## Architecture

```
gitstacker/
├── cli.py          # Command dispatch and help text
├── commands/       # One module per command
├── git_ops.py      # Low-level git operations
├── github.py       # GitHub API integration via gh CLI
├── store.py        # State persistence (.git/gitstacker/state.json)
├── journal.py      # Undo journal (snapshot-based)
└── output.py       # Terminal output formatting
```

State is stored at `.git/gitstacker/state.json` (not committed to source control).

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run specific test categories
pytest tests/unit/
pytest tests/integration/
```

## Requirements

- Python >= 3.9
- Git
- [GitHub CLI (`gh`)](https://cli.github.com) — only required for `gs submit`

## License

MIT
