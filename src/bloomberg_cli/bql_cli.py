"""Minimal Bloomberg BQL command-line transport."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Sequence

from . import __version__
from .cli import _blp, emit


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(
        prog="bloomberg-bql",
        description="Execute one BQL query through the logged-in Bloomberg Terminal.",
    )
    root.add_argument("query", nargs="?", help="Inline BQL query")
    root.add_argument("--file", help="Read BQL from a UTF-8 file; use - for stdin")
    root.add_argument("--format", choices=("json", "csv", "table"), default="json")
    root.add_argument("--show-query", action="store_true")
    root.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return root


def read_query(query: str | None, file: str | None) -> str:
    if query and file:
        raise ValueError("Provide either an inline query or --file, not both")
    if file:
        value = sys.stdin.read() if file == "-" else Path(file).read_text(encoding="utf-8")
    elif query:
        value = query
    elif not sys.stdin.isatty():
        value = sys.stdin.read()
    else:
        raise ValueError("Provide a BQL query, --file PATH, or stdin")
    if not value.strip():
        raise ValueError("BQL query is empty")
    return value.strip()


def run(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        query = read_query(args.query, args.file)
        if args.show_query:
            print(query, file=sys.stderr)
        frame = _blp().bql(query, backend="pandas")
        emit(frame, args.format)
        return 0
    except Exception as exc:
        print(json.dumps({"error": str(exc), "type": type(exc).__name__}), file=sys.stderr)
        return 1


def main() -> None:
    raise SystemExit(run())
