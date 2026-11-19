from datetime import date

import pytest

from turnaround.__main__ import main
from turnaround.core import Application, analyze, business_days, format_table, load, percentile


def test_business_days_within_week():
    assert business_days(date(2026, 3, 2), date(2026, 3, 6)) == 4


def test_business_days_skips_weekend():
    assert business_days(date(2026, 3, 6), date(2026, 3, 9)) == 1


def test_business_days_same_day():
    assert business_days(date(2026, 3, 4), date(2026, 3, 4)) == 0


def test_business_days_holiday():
    assert business_days(date(2026, 3, 2), date(2026, 3, 4), frozenset({date(2026, 3, 3)})) == 1


def test_business_days_reversed():
    with pytest.raises(ValueError):
        business_days(date(2026, 3, 5), date(2026, 3, 4))


def test_percentile():
    assert percentile([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 90) == 9.0


def test_percentile_empty():
    with pytest.raises(ValueError):
        percentile([], 90)


def test_analyze_counts_and_breaches():
    rows = [Application("1", "Electrical", date(2026, 3, 2), date(2026, 3, 4)),
            Application("2", "Electrical", date(2026, 3, 2), date(2026, 3, 20)),
            Application("3", "Electrical", date(2026, 3, 2), None)]
    (s,) = analyze(rows, target_days=10)
    assert (s.issued, s.pending, s.over_target) == (2, 1, 1)
    assert s.median == 8.0


def test_analyze_pending_only_type():
    (s,) = analyze([Application("1", "Roofing", date(2026, 3, 2), None)], 10)
    assert s.median is None and s.pending == 1


def test_analyze_slowest_first():
    rows = [Application("1", "Fast", date(2026, 3, 2), date(2026, 3, 3)),
            Application("2", "Slow", date(2026, 3, 2), date(2026, 3, 13))]
    assert [s.kind for s in analyze(rows, 10)] == ["Slow", "Fast"]


def test_format_table_header_has_target():
    assert "Over 15d" in format_table(analyze([], 15), 15)


def test_load_sample():
    assert len(load("data/applications.csv")) == 60


def test_load_issued_before_applied(tmp_path):
    f = tmp_path / "a.csv"
    f.write_text("permit_id,type,applied,issued\n1,A,2026-03-05,2026-03-01\n")
    with pytest.raises(ValueError, match="issued before applied"):
        load(f)


def test_load_bad_date(tmp_path):
    f = tmp_path / "a.csv"
    f.write_text("permit_id,type,applied,issued\n1,A,03/05/2026,\n")
    with pytest.raises(ValueError, match="line 2"):
        load(f)


def test_cli_ok(capsys):
    assert main(["data/applications.csv", "--target", "10", "--holiday", "2026-01-19"]) == 0
    assert "Over 10d" in capsys.readouterr().out


def test_cli_bad_holiday():
    assert main(["data/applications.csv", "--holiday", "xmas"]) == 2
