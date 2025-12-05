#!/usr/bin/env python3
"""CLI utility to convert strings into jammed Unicode code unit sequences."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, Iterable, List


# Hardcoded sets requested by users for quick reuse.
HARD_CODED_SETS: Dict[str, List[str]] = {
    "symbols": [
        "«∑⫍ʩ௹∏‖﷼₰¯ˇ†₢₥∫–⁄∞₯"
        "∆µ•‰৻৲ʨ⏔ʧª¬∂Ω⋾ↈ◊ﬂı®↹",
        "⁂⋣※⁞૱ɧ⊯⁛ɮ⏓⁊⁒Ϡ⁁⌁ϐͳϟ֏»",
    ],
    "latin": [
        "arras.io",
        "automation",
        "GitHub Copilot",
    ],
}


def strings_to_unicode_chunks(strings: Iterable[str]) -> List[str]:
    """Return each string as consecutive four-digit uppercase hex code units."""
    return ["".join(f"{ord(ch):04X}" for ch in text) for text in strings]


def load_strings(paths: Iterable[Path]) -> List[str]:
    """Load newline-delimited strings from the provided file paths."""
    loaded: List[str] = []
    for path in paths:
        loaded.extend(path.read_text(encoding="utf-8").splitlines())
    return loaded


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Convert input strings into jammed four-digit Unicode code unit sequences."
        )
    )
    parser.add_argument(
        "strings",
        nargs="*",
        help="Strings to convert (can also be read from files).",
    )
    parser.add_argument(
        "-S",
        "--set",
        dest="sets",
        choices=sorted(HARD_CODED_SETS),
        action="append",
        help="Name of a hardcoded string set to include.",
    )
    parser.add_argument(
        "--list-sets",
        action="store_true",
        help="List available hardcoded string set names and exit.",
    )
    parser.add_argument(
        "-f",
        "--file",
        dest="files",
        type=Path,
        action="append",
        default=[],
        help="Path to a newline-delimited file containing strings to convert.",
    )
    parser.add_argument(
        "-s",
        "--show-source",
        action="store_true",
        help="Echo the original string before its Unicode representation.",
    )
    args = parser.parse_args()

    if args.list_sets:
        for name in sorted(HARD_CODED_SETS):
            print(name)
        return

    gathered: List[str] = list(args.strings)
    if args.sets:
        for set_name in args.sets:
            gathered.extend(HARD_CODED_SETS[set_name])
    if args.files:
        gathered.extend(load_strings(args.files))

    if not gathered:
        parser.error("provide at least one string or --file input")

    converted = strings_to_unicode_chunks(gathered)

    for original, jammed in zip(gathered, converted):
        if args.show_source:
            print(f"{original}\t{jammed}")
        else:
            print(jammed)


if __name__ == "__main__":
    main()
