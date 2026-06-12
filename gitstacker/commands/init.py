"""gs init - Initialize gitstacker in the current repo."""

from ..git_ops import is_git_repo, get_default_branch
from ..store import is_initialized, init_state, load_state
from ..output import success, error, info


def cmd_init(args: list[str]) -> None:
    if not is_git_repo():
        error("Not a git repository. Run this command inside a git repo.")
        raise SystemExit(1)

    if is_initialized():
        state = load_state()
        info(f"GitStacker already initialized (trunk: {state['trunk']})")
        return

    trunk = args[0] if args else get_default_branch()
    init_state(trunk)
    success(f"Initialized GitStacker with trunk branch: {trunk}")
    info("Run `gs stack new <name>` to create your first stack.")
