"""Shell completion generation for gitstacker."""


BASH_COMPLETION = '''
_gs_completion() {
    local cur prev commands
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"

    commands="init create stack up down top bottom log restack submit sync delete trunk status modify freeze unfreeze completions aliases help"
    stack_commands="new list switch delete"

    case "${prev}" in
        gs)
            COMPREPLY=( $(compgen -W "${commands}" -- "${cur}") )
            return 0
            ;;
        stack|s)
            COMPREPLY=( $(compgen -W "${stack_commands}" -- "${cur}") )
            return 0
            ;;
        switch|sw)
            # Complete with stack names
            local stacks=$(gs stack list 2>/dev/null | grep -oP '(?<=  [> ] )\\S+(?= )')
            COMPREPLY=( $(compgen -W "${stacks}" -- "${cur}") )
            return 0
            ;;
        delete|del|rm)
            # Complete with branch names in current stack
            local branches=$(git branch --format='%(refname:short)' 2>/dev/null)
            COMPREPLY=( $(compgen -W "${branches} --force" -- "${cur}") )
            return 0
            ;;
        submit|pr)
            COMPREPLY=( $(compgen -W "--draft" -- "${cur}") )
            return 0
            ;;
        log|l)
            COMPREPLY=( $(compgen -W "--all" -- "${cur}") )
            return 0
            ;;
    esac

    COMPREPLY=( $(compgen -W "${commands}" -- "${cur}") )
    return 0
}

complete -F _gs_completion gs
'''

ZSH_COMPLETION = '''
#compdef gs

_gs() {
    local -a commands stack_commands

    commands=(
        'init:Initialize gitstacker in current repo'
        'create:Create a new branch on the current stack'
        'stack:Stack management commands'
        'up:Move up in the stack'
        'down:Move down in the stack'
        'top:Jump to top of stack'
        'bottom:Jump to bottom of stack'
        'log:Show the current stack'
        'restack:Rebase all branches in current stack'
        'submit:Create/update stacked PRs'
        'sync:Fetch trunk and restack'
        'diff:Show diff of current branch vs parent'
        'delete:Remove branch from stack'
        'trunk:Show or set trunk branch'
        'status:Show current state'
        'modify:Amend/commit and auto-restack'
        'undo:Undo last mutating operation'
        'freeze:Freeze a branch'
        'unfreeze:Unfreeze a branch'
        'completions:Output shell completions'
        'aliases:Output shell aliases'
    )

    stack_commands=(
        'new:Create a new stack'
        'list:List all stacks'
        'switch:Switch to a different stack'
        'delete:Delete a stack'
    )

    if (( CURRENT == 2 )); then
        _describe 'command' commands
    elif (( CURRENT == 3 )); then
        case "${words[2]}" in
            stack|s)
                _describe 'stack command' stack_commands
                ;;
            submit|pr)
                _arguments '--draft[Create PRs as drafts]'
                ;;
            log|l)
                _arguments '--all[Show all stacks]'
                ;;
            delete|del|rm)
                _arguments '--force[Also delete git branch]'
                local branches=($(git branch --format='%(refname:short)' 2>/dev/null))
                _describe 'branch' branches
                ;;
        esac
    fi
}

_gs "$@"
'''

FISH_COMPLETION = '''
# Fish shell completions for gs (gitstacker)

set -l commands init create stack up down top bottom log restack submit sync diff delete trunk status modify undo freeze unfreeze completions aliases

complete -c gs -f
complete -c gs -n "not __fish_seen_subcommand_from $commands" -a "init" -d "Initialize gitstacker"
complete -c gs -n "not __fish_seen_subcommand_from $commands" -a "create" -d "Create a new branch"
complete -c gs -n "not __fish_seen_subcommand_from $commands" -a "stack" -d "Stack management"
complete -c gs -n "not __fish_seen_subcommand_from $commands" -a "up" -d "Move up in stack"
complete -c gs -n "not __fish_seen_subcommand_from $commands" -a "down" -d "Move down in stack"
complete -c gs -n "not __fish_seen_subcommand_from $commands" -a "top" -d "Jump to top"
complete -c gs -n "not __fish_seen_subcommand_from $commands" -a "bottom" -d "Jump to bottom"
complete -c gs -n "not __fish_seen_subcommand_from $commands" -a "log" -d "Show stack"
complete -c gs -n "not __fish_seen_subcommand_from $commands" -a "restack" -d "Rebase all branches"
complete -c gs -n "not __fish_seen_subcommand_from $commands" -a "submit" -d "Create/update PRs"
complete -c gs -n "not __fish_seen_subcommand_from $commands" -a "sync" -d "Fetch and restack"
complete -c gs -n "not __fish_seen_subcommand_from $commands" -a "delete" -d "Remove branch"
complete -c gs -n "not __fish_seen_subcommand_from $commands" -a "trunk" -d "Show/set trunk"

# Stack subcommands
complete -c gs -n "__fish_seen_subcommand_from stack" -a "new" -d "Create new stack"
complete -c gs -n "__fish_seen_subcommand_from stack" -a "list" -d "List stacks"
complete -c gs -n "__fish_seen_subcommand_from stack" -a "switch" -d "Switch stack"
complete -c gs -n "__fish_seen_subcommand_from stack" -a "delete" -d "Delete stack"

# Flags
complete -c gs -n "__fish_seen_subcommand_from submit" -l draft -d "Create as draft"
complete -c gs -n "__fish_seen_subcommand_from log" -l all -d "Show all stacks"
complete -c gs -n "__fish_seen_subcommand_from delete" -l force -d "Also delete git branch"
'''


def cmd_completions(args: list[str]) -> None:
    """Output shell completions."""
    shell = args[0] if args else "bash"

    if shell == "bash":
        print(BASH_COMPLETION)
    elif shell == "zsh":
        print(ZSH_COMPLETION)
    elif shell == "fish":
        print(FISH_COMPLETION)
    else:
        print(f"Unsupported shell: {shell}")
        print("Supported: bash, zsh, fish")
        raise SystemExit(1)
