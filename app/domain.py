"""Core domain logic: parse expenses, apply q/p/k rules, aggregate k periods."""

import math
from dataclasses import dataclass
from datetime import datetime
from typing import Callable

from app.schemas import DATETIME_FMT, KPeriod, PPeriod, QPeriod, Transaction


def parse_expense(timestamp: datetime, amount: float) -> tuple[float, float]:
    """Compute ceiling (next multiple of 100) and remanent for one expense."""
    ceiling = math.ceil(amount / 100) * 100
    remanent = ceiling - amount
    return ceiling, remanent


def parse_expenses(
    expenses: list[tuple[datetime, float]],
) -> list[tuple[datetime, float, float, float]]:
    """
    Convert expenses to (date, amount, ceiling, remanent).
    Date is normalized to string format then parsed back for consistency.
    """
    out = []
    for ts, amount in expenses:
        ceiling, remanent = parse_expense(ts, amount)
        # Normalize date to YYYY-MM-DD HH:mm:ss
        date_str = ts.strftime(DATETIME_FMT)
        date = datetime.strptime(date_str, DATETIME_FMT)
        out.append((date, amount, ceiling, remanent))
    return out


def _in_range(d: datetime, start: datetime, end: datetime) -> bool:
    """Inclusive: start <= d <= end."""
    return start <= d <= end


def apply_q_rules(
    transactions: list[tuple[datetime, float, float, float]],
    q_periods: list[QPeriod],
) -> list[tuple[datetime, float, float, float]]:
    """
    Replace remanent with fixed amount when transaction date falls in a q period.
    If multiple q periods match: use the one with latest start; if tie, first in list.
    """
    if not q_periods:
        return list(transactions)

    out = []
    for date, amount, ceiling, remanent in transactions:
        matching = [
            (q.start, q.fixed)
            for q in q_periods
            if _in_range(date, q.start, q.end)
        ]
        if matching:
            # Sort by start desc (latest first), then take first
            matching.sort(key=lambda x: x[0], reverse=True)
            _, fixed = matching[0]
            remanent = fixed
        out.append((date, amount, ceiling, remanent))
    return out


def apply_p_rules(
    transactions: list[tuple[datetime, float, float, float]],
    p_periods: list[PPeriod],
) -> list[tuple[datetime, float, float, float]]:
    """
    Add all matching p periods' extra to remanent (cumulative).
    """
    if not p_periods:
        return list(transactions)

    out = []
    for date, amount, ceiling, remanent in transactions:
        extra = sum(
            p.extra for p in p_periods
            if _in_range(date, p.start, p.end)
        )
        out.append((date, amount, ceiling, remanent + extra))
    return out


def aggregate_k_periods(
    transactions: list[tuple[datetime, float, float, float]],
    k_periods: list[KPeriod],
) -> list[tuple[datetime, datetime, float]]:
    """
    For each k period, sum remanent of transactions whose date is in [start, end] (inclusive).
    Returns list of (start, end, amount).
    """
    result = []
    for k in k_periods:
        total = sum(
            remanent
            for date, _amount, _ceiling, remanent in transactions
            if _in_range(date, k.start, k.end)
        )
        result.append((k.start, k.end, total))
    return result


def build_transactions(
    raw: list[tuple[datetime, float, float, float]],
) -> list[Transaction]:
    """Convert list of (date, amount, ceiling, remanent) to Transaction models."""
    return [
        Transaction(date=date, amount=amount, ceiling=ceiling, remanent=remanent)
        for date, amount, ceiling, remanent in raw
    ]


def run_pipeline(
    expenses: list[tuple[datetime, float]],
    q_periods: list[QPeriod],
    p_periods: list[PPeriod],
    k_periods: list[KPeriod],
) -> tuple[
    list[tuple[datetime, float, float, float]],
    list[tuple[datetime, datetime, float]],
]:
    """
    Full pipeline: parse -> q -> p, then aggregate k.
    Returns (transactions as tuples, k_sums as (start, end, amount)).
    """
    step = parse_expenses(expenses)
    step = apply_q_rules(step, q_periods)
    step = apply_p_rules(step, p_periods)
    k_sums = aggregate_k_periods(step, k_periods)
    return step, k_sums
