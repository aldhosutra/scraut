"""
lib/utils/date_utils.py
Sprint date calculations and scheduling utilities.
"""
from datetime import date, timedelta, datetime
from typing import Optional
import pytz


def get_sprint_dates(sprint_num: int, config: dict) -> tuple[date, date]:
    """
    Calculate start and end dates for a given sprint number.
    Uses sprint.length_days and sprint.start_day from config.
    """
    sprint_cfg = config["sprint"]
    length = sprint_cfg["length_days"]
    epoch = date.today()  # Fallback; actual epoch set in scraut.yml after first sprint

    start = epoch + timedelta(days=(sprint_num - 1) * length)
    end = start + timedelta(days=length - 1)
    return start, end


def working_days_remaining(end_date: date) -> int:
    """Count working days (Mon-Fri) between today and end_date."""
    today = date.today()
    count = 0
    current = today
    while current <= end_date:
        if current.weekday() < 5:  # Monday=0, Friday=4
            count += 1
        current += timedelta(days=1)
    return count


def days_until_sprint_end(end_date: date) -> int:
    """Alias for working_days_remaining — named per CLAUDE.md convention."""
    return working_days_remaining(end_date)


def working_days_elapsed(start_date: date) -> int:
    """Count working days from start_date to today."""
    today = date.today()
    count = 0
    current = start_date
    while current < today:
        if current.weekday() < 5:
            count += 1
        current += timedelta(days=1)
    return count


def is_weekday(d: Optional[date] = None) -> bool:
    if d is None:
        d = date.today()
    return d.weekday() < 5


# Alias per CLAUDE.md convention
is_working_day = is_weekday


def localize_time(naive_dt: datetime, timezone_str: str) -> datetime:
    tz = pytz.timezone(timezone_str)
    return tz.localize(naive_dt)
