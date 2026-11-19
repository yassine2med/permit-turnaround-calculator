"""Command line entry: python -m turnaround <csv> --target 15 [--holiday YYYY-MM-DD]."""
from __future__ import annotations

import argparse
import sys
from datetime import date

from .core import analyze, format_table, load


def main(argv: list[str] | None = None) -> int:
    """Run the CLI. Exit code 0 on success, 2 on bad input."""
    parser = argparse.ArgumentParser(prog="turnaround", description="Permit turnaround in business days.")
    parser.add_argument("csv")
    parser.add_argument("--target", type=int, default=15, help="target business days (default 15)")
    parser.add_argument("--holiday", action="append", default=[], help="holiday date, repeatable")
    args = parser.parse_args(argv)
    try:
        holidays = frozenset(date.fromisoformat(h) for h in args.holiday)
        print(format_table(analyze(load(args.csv), args.target, holidays), args.target))
    except (ValueError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
