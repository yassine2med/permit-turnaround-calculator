"""Permit turnaround time in business days: median, mean, 90th percentile and target breaches."""
from __future__ import annotations

import csv
import math
import statistics
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

REQUIRED = ("permit_id", "type", "applied", "issued")


@dataclass(frozen=True)
class Application:
    permit_id: str
    kind: str
    applied: date
    issued: date | None


@dataclass(frozen=True)
class TypeStats:
    kind: str
    issued: int
    pending: int
    median: float | None
    mean: float | None
    p90: float | None
    over_target: int


def business_days(start: date, end: date, holidays: frozenset[date] = frozenset()) -> int:
    """Count business days after `start` up to and including `end`. Weekends and holidays are skipped."""
    if end < start:
        raise ValueError("end is before start")
    days = 0
    current = start
    while current < end:
        current += timedelta(days=1)
        if current.weekday() < 5 and current not in holidays:
            days += 1
    return days


def load(path: str | Path) -> list[Application]:
    """Read applications from CSV. A blank issued value means still pending."""
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        missing = [c for c in REQUIRED if c not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"missing columns: {', '.join(missing)}")
        rows = []
        for line, row in enumerate(reader, start=2):
            try:
                applied = date.fromisoformat(row["applied"])
                issued = date.fromisoformat(row["issued"]) if row["issued"].strip() else None
            except ValueError as exc:
                raise ValueError(f"line {line}: {exc}") from exc
            if issued is not None and issued < applied:
                raise ValueError(f"line {line}: issued before applied")
            rows.append(Application(row["permit_id"].strip(), row["type"].strip(), applied, issued))
    return rows


def percentile(values: list[int], pct: float) -> float:
    """Nearest-rank percentile of a non-empty list."""
    if not values:
        raise ValueError("no values")
    ordered = sorted(values)
    return float(ordered[max(1, math.ceil(pct / 100 * len(ordered))) - 1])


def analyze(rows: list[Application], target_days: int, holidays: frozenset[date] = frozenset()) -> list[TypeStats]:
    """Stats per permit type, slowest median first."""
    groups: dict[str, list[Application]] = {}
    for r in rows:
        groups.setdefault(r.kind, []).append(r)
    out = []
    for kind, items in groups.items():
        days = [business_days(r.applied, r.issued, holidays) for r in items if r.issued]
        out.append(TypeStats(kind, len(days), len(items) - len(days),
                             statistics.median(days) if days else None,
                             statistics.mean(days) if days else None,
                             percentile(days, 90) if days else None,
                             sum(1 for d in days if d > target_days)))
    return sorted(out, key=lambda s: (s.median is None, -(s.median or 0), s.kind))


def format_table(stats: list[TypeStats], target_days: int) -> str:
    """Plain text table."""
    def num(v: float | None) -> str:
        return "-" if v is None else f"{v:.1f}"
    head = f"{'Type':<14}{'Issued':>7}{'Pending':>8}{'Median':>8}{'Mean':>7}{'P90':>6}{'Over ' + str(target_days) + 'd':>9}"
    lines = [head, "-" * len(head)]
    for s in stats:
        lines.append(f"{s.kind:<14}{s.issued:>7}{s.pending:>8}{num(s.median):>8}{num(s.mean):>7}{num(s.p90):>6}{s.over_target:>9}")
    return "\n".join(lines)
