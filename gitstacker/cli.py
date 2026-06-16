"""
GitStacker CLI entry point.

Usage:
  gs <command> [options]

Commands:
  init [trunk]            Initialize gitstacker (default trunk: main)
  create <name>           Create a new branch on the current stack
  stack new <name>        Start a new stack
  stack list              List all stacks
  stack switch <name>     Switch to a different stack
  stack delete <name>     Delete a stack (keeps git branches)
  up [n]                  Move up n branches (default: 1)
  down [n]                Move down n branches (default: 1)
  top                     Jump to top of stack
  bottom                  Jump to bottom of stack
  log [--all]             Show current stack (or all with --all)
  modify [flags]          Amend/commit and auto-restack upstack
  restack                 Rebase all branches in current stack
  submit [--draft]        Create/update stacked PRs
  sync                    Fetch trunk, update, and restack
  delete [name] [--force] Remove branch from stack
  trunk [name]            Show or set trunk branch
"""

import sys
from .output import bold, dim, cyan, error as error_out

VERSION = "0.1.0"

HELP_TEXT = f"""
{bold("GitStacker")} {dim(f"v{VERSION}")} — Git branch stacking tool

{bold("USAGE")}
  {cyan("gs")} <command> [options]

{bold("COMMANDS")}
  {cyan("init")} [trunk]            Initialize gitstacker (default trunk: main)
  {cyan("create")} <name>           Create a new branch on the current stack
  {cyan("stack new")} <name>        Start a new stack
  {cyan("stack list")}              List all stacks
  {cyan("stack switch")} <name>     Switch to a different stack
  {cyan("stack delete")} <name>     Delete a stack (keeps git branches)
  {cyan("up")} [n]                  Move up n branches (default: 1)
  {cyan("down")} [n]                Move down n branches (default: 1)
  {cyan("top")}                     Jump to top of stack
  {cyan("bottom")}                  Jump to bottom of stack
  {cyan("log")} [--all]             Show current stack (or all with --all)
  {cyan("restack")}                 Rebase all branches in current stack
  {cyan("submit")} [--draft]        Create/update stacked PRs
  {cyan("sync")}                    Fetch trunk, update, and restack
  {cyan("diff")} [--stat]          Show diff of current branch vs parent
  {cyan("delete")} [name] [--force] Remove branch from stack
  {cyan("trunk")} [name]            Show or set trunk branch
  {cyan("status")} [--json]         Show current state (JSON for AI agents)
  {cyan("undo")}                    Undo the last mutating operation
  {cyan("modify")} [flags]            Amend/commit and auto-restack upstack
  {cyan("freeze")} [name]            Freeze a branch (skip restack, block create)
  {cyan("unfreeze")} [name]          Unfreeze a branch
  {cyan("completions")} <shell>     Output shell completions (bash/zsh/fish)
  {cyan("aliases")} [shell]          Output shell aliases (eval "$(gs aliases)")

{bold("EXAMPLES")}
  {dim("# Start a new feature stack")}
  gs init
  gs stack new auth-feature
  gs create auth-api
  {dim("# ... make commits ...")}
  gs create auth-ui
  {dim("# ... make commits ...")}

  {dim("# View the stack")}
  gs log

  {dim("# Rebase entire stack after trunk updates")}
  gs sync

  {dim("# Submit all PRs at once")}
  gs submit

  {dim("# Navigate the stack")}
  gs up
  gs down
  gs top
  gs bottom

{bold("ALIASES")}
  c     = create        gsc    = gs create
  s     = stack         gss    = gs stack
  u     = up            gsu    = gs up
  d     = down          gsd    = gs down
  l     = log           gsl    = gs log
  m     = modify        gsm    = gs modify
  rs    = restack       gsrs   = gs restack
  pr    = submit        gspr   = gs submit
  rm    = delete        gsrm   = gs delete
  bot   = bottom        gsbot  = gs bottom
                        gstop  = gs top
                        gssync = gs sync
                        gsdiff = gs diff
                        gsst   = gs status

  {dim("# Install terminal aliases:")}
  eval "$(gs aliases)"          {dim("# bash/zsh")}
  gs aliases fish | source      {dim("# fish")}

{bold("OPTIONS")}
  --help, -h      Show this help message
  --version, -v   Show version
"""


def main() -> None:
    args = sys.argv[1:]
    command = args[0] if args else None
    command_args = args[1:] if args else []

    if not command or command in ("--help", "-h", "help"):
        print(HELP_TEXT)
        sys.exit(0)

    if command in ("--version", "-v"):
        print(f"gitstacker v{VERSION}")
        sys.exit(0)

    try:
        if command == "init":
            from .commands.init import cmd_init
            cmd_init(command_args)

        elif command in ("create", "c"):
            from .commands.create import cmd_create
            cmd_create(command_args)

        elif command in ("stack", "s"):
            from .commands.stack import cmd_stack
            cmd_stack(command_args)

        elif command in ("up", "u"):
            from .commands.navigate import cmd_navigate
            cmd_navigate("up", command_args)

        elif command in ("down", "d"):
            from .commands.navigate import cmd_navigate
            cmd_navigate("down", command_args)

        elif command == "top":
            from .commands.navigate import cmd_navigate
            cmd_navigate("top", command_args)

        elif command in ("bottom", "bot"):
            from .commands.navigate import cmd_navigate
            cmd_navigate("bottom", command_args)

        elif command in ("log", "l"):
            from .commands.log import cmd_log
            cmd_log(command_args)

        elif command in ("restack", "rs"):
            from .commands.restack import cmd_restack
            cmd_restack(command_args)

        elif command in ("submit", "pr"):
            from .commands.submit import cmd_submit
            cmd_submit(command_args)

        elif command == "sync":
            from .commands.sync import cmd_sync
            cmd_sync(command_args)

        elif command == "diff":
            from .commands.diff import cmd_diff
            cmd_diff(command_args)

        elif command in ("delete", "del", "rm"):
            from .commands.delete import cmd_delete
            cmd_delete(command_args)

        elif command == "trunk":
            from .commands.trunk import cmd_trunk
            cmd_trunk(command_args)

        elif command == "completions":
            from .commands.completions import cmd_completions
            cmd_completions(command_args)

        elif command == "aliases":
            from .commands.aliases import cmd_aliases
            cmd_aliases(command_args)

        elif command == "status":
            from .commands.status import cmd_status
            cmd_status(command_args)

        elif command == "undo":
            from .commands.undo import cmd_undo
            cmd_undo(command_args)

        elif command in ("modify", "m"):
            from .commands.modify import cmd_modify
            cmd_modify(command_args)

        elif command == "freeze":
            from .commands.freeze import cmd_freeze
            cmd_freeze(command_args)

        elif command == "unfreeze":
            from .commands.freeze import cmd_unfreeze
            cmd_unfreeze(command_args)

        else:
            error_out(f"Unknown command: {command}")
            print(f"Run {cyan('gs --help')} for usage.")
            sys.exit(1)

    except SystemExit:
        raise
    except Exception as e:
        error_out(str(e))
        if "--debug" in args:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
