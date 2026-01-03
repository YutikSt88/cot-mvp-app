from __future__ import annotations
from datetime import date, datetime, timedelta

def today_utc_date() -> date:
    return datetime.utcnow().date()

def year_range(start_year: int, end_year: int) -> list[int]:
    if end_year < start_year:
        return []
    return list(range(start_year, end_year + 1))

def to_date(x) -> date:
    if isinstance(x, date):
        return x
    return datetime.strptime(str(x), "%Y-%m-%d").date()
