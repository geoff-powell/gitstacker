"""Interactive prompts for gitstacker commands."""

import sys


def offer_track_current_branch(state: dict, branch: str):
    """If branch is not tracked, offer to track it.
    
    Returns the stack dict if tracking succeeded.
    Raises SystemExit if user declines or tracking fails.
    """
    from .store import get_current_stack, save_state
    from .commands.track import track_branch
    from .output import error
    
    stack = get_current_stack(state, branch)
    if stack:
        return stack
    
    # Check if stdin is interactive
    if not sys.stdin.isatty():
        error(f'Branch "{branch}" is not tracked in any stack.')
        raise SystemExit(1)
    
    print(f'Branch "{branch}" is not tracked in any stack.')
    try:
        response = input("Track it now? [Y/n]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        raise SystemExit(1)
    
    if response in ("", "y", "yes"):
        # Find active stack
        active_stack = None
        if state.get("current_stack"):
            active_stack = state["stacks"].get(state["current_stack"])
        
        if not active_stack:
            from .store import create_stack
            stack_name = branch
            try:
                active_stack = create_stack(state, stack_name, state["trunk"])
                state["current_stack"] = stack_name
            except RuntimeError:
                active_stack = state["stacks"].get(stack_name)
                if active_stack:
                    state["current_stack"] = stack_name
                else:
                    error("Could not create or find a stack.")
                    raise SystemExit(1)
        
        if track_branch(branch, state, active_stack):
            save_state(state)
            return get_current_stack(state, branch)
        else:
            raise SystemExit(1)
    else:
        raise SystemExit(1)
