"""
lib/utils/date_utils.py
Sprint date calculations and scheduling utilities.
"""
from datetime import date, timedelta, datetime
from pathlib import Path
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


def is_working_day(d: Optional[date] = None,
                   config: Optional[dict] = None,
                   scraut_root: Optional[Path] = None) -> bool:
    """Return True if d is a working day (weekday and not a holiday).

    Pass config to enable holiday awareness. Without config only weekends
    are excluded, preserving backward compatibility for callers that don't
    have config available.
    """
    if d is None:
        d = date.today()
    if d.weekday() >= 5:
        return False
    if config and config.get("holidays"):
        from scraut.platform.utils.holiday_utils import is_holiday
        return not is_holiday(d, config, scraut_root)
    return True


# Backward-compatible alias
is_weekday = is_working_day


def working_days_remaining(end_date: date,
                            config: Optional[dict] = None,
                            scraut_root: Optional[Path] = None) -> int:
    """Count working days (Mon–Fri, minus holidays) between today and end_date."""
    today = date.today()
    count = 0
    current = today
    while current <= end_date:
        if is_working_day(current, config, scraut_root):
            count += 1
        current += timedelta(days=1)
    return count


def days_until_sprint_end(end_date: date,
                           config: Optional[dict] = None,
                           scraut_root: Optional[Path] = None) -> int:
    """Alias for working_days_remaining — named per CLAUDE.md convention."""
    return working_days_remaining(end_date, config, scraut_root)


def working_days_elapsed(start_date: date,
                          config: Optional[dict] = None,
                          scraut_root: Optional[Path] = None) -> int:
    """Count working days from start_date to today."""
    today = date.today()
    count = 0
    current = start_date
    while current < today:
        if is_working_day(current, config, scraut_root):
            count += 1
        current += timedelta(days=1)
    return count


def localize_time(naive_dt: datetime, timezone_str: str) -> datetime:
    tz = pytz.timezone(timezone_str)
    return tz.localize(naive_dt)
