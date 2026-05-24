"""test/unit/test_date_utils.py"""
import pytest
from datetime import date, timedelta
from freezegun import freeze_time
from scraut.platform.utils.date_utils import (
    get_sprint_dates, is_working_day, days_until_sprint_end,
    working_days_remaining,
)


@pytest.mark.unit
def test_get_sprint_dates_returns_tuple(config):
    start, end = get_sprint_dates(1, config)
    assert isinstance(start, date)
    assert isinstance(end, date)
    assert end > start


@pytest.mark.unit
def test_sprint_dates_length(config):
    start, end = get_sprint_dates(1, config)
    delta = (end - start).days + 1
    assert delta == config["sprint"]["length_days"]


@pytest.mark.unit
@freeze_time("2026-05-25")
def test_is_working_day_true_on_weekday():
    assert is_working_day(date(2026, 5, 25)) is True


@pytest.mark.unit
@freeze_time("2026-05-24")
def test_is_working_day_false_on_weekend():
    assert is_working_day(date(2026, 5, 24)) is False


@pytest.mark.unit
def test_days_until_sprint_end_nonzero_for_future():
    future_date = date.today() + timedelta(days=5)
    result = days_until_sprint_end(future_date)
    assert result >= 0
