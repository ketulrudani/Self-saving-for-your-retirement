# Test type: Unit
# Validation: Ceiling/remanent calculation, q period (fixed override, latest start), p period (extra sum), k period aggregation.
# Command: uv run pytest test/test_domain.py -v

from datetime import datetime

import pytest

from app import domain
from app.schemas import KPeriod, PPeriod, QPeriod

DATETIME_FMT = "%Y-%m-%d %H:%M:%S"


def _dt(s: str) -> datetime:
    return datetime.strptime(s, DATETIME_FMT)


def test_parse_expense_ceiling_remanent():
    ceiling, remanent = domain.parse_expense(_dt("2023-10-12 20:15:00"), 250)
    assert ceiling == 300
    assert remanent == 50

    ceiling, remanent = domain.parse_expense(_dt("2023-02-28 15:49:00"), 375)
    assert ceiling == 400
    assert remanent == 25

    ceiling, remanent = domain.parse_expense(_dt("2023-07-01 21:59:00"), 620)
    assert ceiling == 700
    assert remanent == 80

    ceiling, remanent = domain.parse_expense(_dt("2023-12-17 08:09:00"), 480)
    assert ceiling == 500
    assert remanent == 20


def test_parse_expenses():
    expenses = [
        (_dt("2023-10-12 20:15:00"), 250),
        (_dt("2023-02-28 15:49:00"), 375),
    ]
    raw = domain.parse_expenses(expenses)
    assert len(raw) == 2
    assert raw[0][1] == 250 and raw[0][2] == 300 and raw[0][3] == 50
    assert raw[1][1] == 375 and raw[1][2] == 400 and raw[1][3] == 25


def test_apply_q_rules_empty():
    raw = [(_dt("2023-07-01 12:00:00"), 620, 700, 80)]
    out = domain.apply_q_rules(raw, [])
    assert out[0][3] == 80


def test_apply_q_rules_fixed_override():
    raw = [
        (_dt("2023-10-12 20:15:00"), 250, 300, 50),
        (_dt("2023-07-01 21:59:00"), 620, 700, 80),
        (_dt("2023-12-17 08:09:00"), 480, 500, 20),
    ]
    q = [QPeriod(fixed=0, start=_dt("2023-07-01 00:00:00"), end=_dt("2023-07-31 23:59:00"))]
    out = domain.apply_q_rules(raw, q)
    assert out[0][3] == 50
    assert out[1][3] == 0
    assert out[2][3] == 20


def test_apply_q_rules_latest_start_wins():
    raw = [(_dt("2023-07-15 12:00:00"), 100, 200, 100)]
    q = [
        QPeriod(fixed=10, start=_dt("2023-07-01 00:00:00"), end=_dt("2023-07-31 23:59:00")),
        QPeriod(fixed=20, start=_dt("2023-07-10 00:00:00"), end=_dt("2023-07-31 23:59:00")),
    ]
    out = domain.apply_q_rules(raw, q)
    assert out[0][3] == 20


def test_apply_p_rules():
    raw = [
        (_dt("2023-10-12 20:15:00"), 250, 300, 50),
        (_dt("2023-02-28 15:49:00"), 375, 400, 25),
    ]
    p = [PPeriod(extra=25, start=_dt("2023-10-01 08:00:00"), end=_dt("2023-12-31 19:59:00"))]
    out = domain.apply_p_rules(raw, p)
    assert out[0][3] == 75
    assert out[1][3] == 25


def test_aggregate_k_periods():
    raw = [
        (_dt("2023-10-12 20:15:00"), 250, 300, 75),
        (_dt("2023-02-28 15:49:00"), 375, 400, 25),
        (_dt("2023-07-01 21:59:00"), 620, 700, 0),
        (_dt("2023-12-17 08:09:00"), 480, 500, 45),
    ]
    k = [
        KPeriod(start=_dt("2023-03-01 00:00:00"), end=_dt("2023-11-30 23:59:00")),
        KPeriod(start=_dt("2023-01-01 00:00:00"), end=_dt("2023-12-31 23:59:00")),
    ]
    sums = domain.aggregate_k_periods(raw, k)
    assert sums[0][2] == 75
    assert sums[1][2] == 145


def test_run_pipeline_pdf_example():
    expenses = [
        (_dt("2023-10-12 20:15:00"), 250),
        (_dt("2023-02-28 15:49:00"), 375),
        (_dt("2023-07-01 21:59:00"), 620),
        (_dt("2023-12-17 08:09:00"), 480),
    ]
    q = [QPeriod(fixed=0, start=_dt("2023-07-01 00:00:00"), end=_dt("2023-07-31 23:59:00"))]
    p = [PPeriod(extra=25, start=_dt("2023-10-01 08:00:00"), end=_dt("2023-12-31 19:59:00"))]
    k = [
        KPeriod(start=_dt("2023-03-01 00:00:00"), end=_dt("2023-11-30 23:59:00")),
        KPeriod(start=_dt("2023-01-01 00:00:00"), end=_dt("2023-12-31 23:59:00")),
    ]
    transactions, k_sums = domain.run_pipeline(expenses, q, p, k)
    assert k_sums[0][2] == 75
    assert k_sums[1][2] == 145
