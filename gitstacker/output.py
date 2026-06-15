"""
Terminal output utilities — colors, symbols, and formatted messages.
"""

import os
import sys

# Color support detection
_COLOR = (
    os.environ.get("NO_COLOR") is None
    and hasattr(sys.stdout, "isatty")
    and sys.stdout.isatty()
)


def _wrap(code: int, reset: int):
    def inner(text: str) -> str:
        if not _COLOR:
            return text
        return f"\033[{code}m{text}\033[{reset}m"
    return inner


bold = _wrap(1, 22)
dim = _wrap(2, 22)
italic = _wrap(3, 23)
red = _wrap(31, 39)
green = _wrap(32, 39)
yellow = _wrap(33, 39)
blue = _wrap(34, 39)
magenta = _wrap(35, 39)
cyan = _wrap(36, 39)
gray = _wrap(90, 39)


FROZEN_SYMBOL = "\u2744" if _COLOR else "[frozen]"  # snowflake: ❄


class symbols:
    arrow = "\u2192" if _COLOR else "->"
    check = "\u2713" if _COLOR else "[ok]"
    cross = "\u2717" if _COLOR else "[err]"
    dot = "\u25cf" if _COLOR else "*"
    circle = "\u25cb" if _COLOR else "o"
    line = "\u2502" if _COLOR else "|"
    branch = "\u251c" if _COLOR else "|"
    corner = "\u2514" if _COLOR else "`"
    tee = "\u252c" if _COLOR else "+"
    pointer = "\u25b8" if _COLOR else ">"


def success(msg: str) -> None:
    print(f"{green(symbols.check)} {msg}")


def error(msg: str) -> None:
    print(f"{red(symbols.cross)} {msg}", file=sys.stderr)


def warn(msg: str) -> None:
    print(f"{yellow('!')} {msg}")


def info(msg: str) -> None:
    print(f"{blue(symbols.dot)} {msg}")


def heading(msg: str) -> None:
    print(f"\n{bold(msg)}")
