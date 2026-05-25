"""test/unit/test_holiday_utils.py — holiday utility and work_days unit tests"""
import json
import pytest
from datetime import date
from pathlib import Path
from unittest.mock import patch, MagicMock

from scraut.platform.utils.holiday_utils import (
    get_public_holidays, get_all_holidays, is_holiday, clear_cache,
)
from scraut.platform.utils.config import get_work_days
from scraut.platform.utils.date_utils import is_working_day


@pytest.fixture(autouse=True)
def reset_holiday_cache():
    """Clear in-process cache before every test."""
    clear_cache()
    yield
    clear_cache()


def _cfg(country_code="", extra_dates=None, skip_dates=None):
    return {
        "holidays": {
            "country_code": country_code,
            "extra_dates": extra_dates or [],
            "skip_dates": skip_dates or [],
        }
    }


# ── get_all_holidays ──────────────────────────────────────────────────────────

@pytest.mark.unit
def test_empty_config_returns_empty_set():
    assert get_all_holidays(2026, {}) == set()


@pytest.mark.unit
def test_missing_holidays_key_returns_empty_set():
    assert get_all_holidays(2026, {"sprint": {"current_sprint": 1}}) == set()


@pytest.mark.unit
def test_extra_dates_added():
    cfg = _cfg(extra_dates=["2026-08-17", "2026-12-26"])
    result = get_all_holidays(2026, cfg)
    assert date(2026, 8, 17) in result
    assert date(2026, 12, 26) in result


@pytest.mark.unit
def test_skip_dates_remove_from_extra():
    cfg = _cfg(extra_dates=["2026-01-01"], skip_dates=["2026-01-01"])
    result = get_all_holidays(2026, cfg)
    assert date(2026, 1, 1) not in result


@pytest.mark.unit
def test_invalid_date_string_is_ignored():
    cfg = _cfg(extra_dates=["not-a-date", "2026-08-17"])
    result = get_all_holidays(2026, cfg)
    assert date(2026, 8, 17) in result
    assert len(result) == 1


@pytest.mark.unit
def test_no_api_call_when_country_code_blank(tmp_path):
    cfg = _cfg(country_code="")
    with patch("scraut.platform.utils.holiday_utils._fetch_nager") as mock_fetch:
        get_all_holidays(2026, cfg, tmp_path)
        mock_fetch.assert_not_called()


# ── get_public_holidays — API + cache ─────────────────────────────────────────

@pytest.mark.unit
def test_api_result_is_cached_to_disk(tmp_path):
    with patch("scraut.platform.utils.holiday_utils._fetch_nager",
               return_value=["2026-01-01", "2026-12-25"]) as mock_fetch:
        result = get_public_holidays(2026, "US", tmp_path)

    mock_fetch.assert_called_once_with(2026, "US")
    assert date(2026, 1, 1) in result
    cache_file = tmp_path / "holidays" / "US" / "2026.json"
    assert cache_file.exists()
    assert json.loads(cache_file.read_text()) == ["2026-01-01", "2026-12-25"]


@pytest.mark.unit
def test_cache_hit_skips_api(tmp_path):
    cache_file = tmp_path / "holidays" / "US" / "2026.json"
    cache_file.parent.mkdir(parents=True)
    cache_file.write_text(json.dumps(["2026-07-04"]))

    with patch("scraut.platform.utils.holiday_utils._fetch_nager") as mock_fetch:
        result = get_public_holidays(2026, "US", tmp_path)

    mock_fetch.assert_not_called()
    assert date(2026, 7, 4) in result


@pytest.mark.unit
def test_corrupt_cache_falls_back_to_api(tmp_path):
    cache_file = tmp_path / "holidays" / "US" / "2026.json"
    cache_file.parent.mkdir(parents=True)
    cache_file.write_text("not valid json{{{")

    with patch("scraut.platform.utils.holiday_utils._fetch_nager",
               return_value=["2026-01-01"]) as mock_fetch:
        result = get_public_holidays(2026, "US", tmp_path)

    mock_fetch.assert_called_once()
    assert date(2026, 1, 1) in result


@pytest.mark.unit
def test_api_failure_returns_empty_set(tmp_path):
    with patch("scraut.platform.utils.holiday_utils._fetch_nager", return_value=[]):
        result = get_public_holidays(2026, "XX", tmp_path)
    assert result == set()


@pytest.mark.unit
def test_in_process_cache_avoids_repeated_disk_reads(tmp_path):
    cache_file = tmp_path / "holidays" / "ID" / "2026.json"
    cache_file.parent.mkdir(parents=True)
    cache_file.write_text(json.dumps(["2026-08-17"]))

    with patch.object(Path, "read_text", wraps=cache_file.read_text) as mock_read:
        get_public_holidays(2026, "ID", tmp_path)
        get_public_holidays(2026, "ID", tmp_path)  # second call — in-process cache
        # read_text should only be called for the cache file once
        assert mock_read.call_count <= 1


# ── is_holiday ────────────────────────────────────────────────────────────────

@pytest.mark.unit
def test_is_holiday_true_for_extra_date():
    cfg = _cfg(extra_dates=["2026-08-17"])
    assert is_holiday(date(2026, 8, 17), cfg) is True


@pytest.mark.unit
def test_is_holiday_false_for_regular_day():
    cfg = _cfg(extra_dates=["2026-08-17"])
    assert is_holiday(date(2026, 8, 18), cfg) is False


@pytest.mark.unit
def test_is_holiday_false_after_skip_date():
    cfg = _cfg(extra_dates=["2026-08-17"], skip_dates=["2026-08-17"])
    assert is_holiday(date(2026, 8, 17), cfg) is False


# ── is_working_day integration ────────────────────────────────────────────────

@pytest.mark.unit
def test_is_working_day_false_on_weekend():
    saturday = date(2026, 5, 23)
    assert saturday.weekday() == 5
    assert is_working_day(saturday) is False


@pytest.mark.unit
def test_is_working_day_true_on_weekday_no_config():
    monday = date(2026, 5, 25)
    assert monday.weekday() == 0
    assert is_working_day(monday) is True


@pytest.mark.unit
def test_is_working_day_false_on_holiday_with_config():
    cfg = _cfg(extra_dates=["2026-05-25"])
    monday = date(2026, 5, 25)
    assert monday.weekday() == 0  # it's a weekday
    assert is_working_day(monday, cfg) is False


@pytest.mark.unit
def test_is_working_day_true_on_skip_date_override():
    cfg = _cfg(extra_dates=["2026-05-25"], skip_dates=["2026-05-25"])
    monday = date(2026, 5, 25)
    assert is_working_day(monday, cfg) is True


@pytest.mark.unit
def test_is_working_day_no_holidays_key_behaves_as_weekday_check():
    """Config with no holidays section should not raise."""
    cfg = {"sprint": {"current_sprint": 1}}
    monday = date(2026, 5, 25)
    assert is_working_day(monday, cfg) is True


# ── get_work_days ─────────────────────────────────────────────────────────────

def _sprint_cfg(work_days=None):
    base = {"sprint": {"current_sprint": 1}}
    if work_days is not None:
        base["sprint"]["work_days"] = work_days
    return base


@pytest.mark.unit
def test_work_days_default_is_mon_fri():
    result = get_work_days(_sprint_cfg())
    assert result == frozenset({0, 1, 2, 3, 4})


@pytest.mark.unit
def test_work_days_empty_list_uses_default():
    result = get_work_days(_sprint_cfg(work_days=[]))
    assert result == frozenset({0, 1, 2, 3, 4})


@pytest.mark.unit
def test_work_days_sun_thu_schedule():
    cfg = _sprint_cfg(work_days=["sunday", "monday", "tuesday", "wednesday", "thursday"])
    result = get_work_days(cfg)
    assert result == frozenset({6, 0, 1, 2, 3})


@pytest.mark.unit
def test_work_days_four_day_week():
    cfg = _sprint_cfg(work_days=["monday", "tuesday", "wednesday", "thursday"])
    result = get_work_days(cfg)
    assert result == frozenset({0, 1, 2, 3})
    assert 4 not in result   # Friday excluded


@pytest.mark.unit
def test_work_days_invalid_name_ignored():
    cfg = _sprint_cfg(work_days=["monday", "funday"])
    result = get_work_days(cfg)
    assert result == frozenset({0})


@pytest.mark.unit
def test_work_days_case_insensitive():
    cfg = _sprint_cfg(work_days=["Monday", "FRIDAY"])
    result = get_work_days(cfg)
    assert result == frozenset({0, 4})


# ── is_working_day with work_days config ──────────────────────────────────────

@pytest.mark.unit
def test_is_working_day_friday_excluded_in_4day_week():
    friday = date(2026, 5, 29)    # weekday() == 4
    cfg = _sprint_cfg(work_days=["monday", "tuesday", "wednesday", "thursday"])
    assert is_working_day(friday, cfg) is False


@pytest.mark.unit
def test_is_working_day_sunday_working_in_sun_thu_schedule():
    sunday = date(2026, 5, 24)    # weekday() == 6
    cfg = _sprint_cfg(work_days=["sunday", "monday", "tuesday", "wednesday", "thursday"])
    assert is_working_day(sunday, cfg) is True


@pytest.mark.unit
def test_is_working_day_saturday_non_working_in_sun_thu():
    saturday = date(2026, 5, 23)  # weekday() == 5
    cfg = _sprint_cfg(work_days=["sunday", "monday", "tuesday", "wednesday", "thursday"])
    assert is_working_day(saturday, cfg) is False


@pytest.mark.unit
def test_is_working_day_holiday_on_work_day_is_false():
    """A day in work_days is still non-working if it's a holiday."""
    monday = date(2026, 5, 25)
    cfg = {
        "sprint": {"work_days": ["monday", "tuesday", "wednesday", "thursday", "friday"]},
        "holidays": {"country_code": "", "extra_dates": ["2026-05-25"], "skip_dates": []},
    }
    assert is_working_day(monday, cfg) is False


@pytest.mark.unit
def test_is_working_day_no_config_falls_back_to_mon_fri():
    friday = date(2026, 5, 29)
    saturday = date(2026, 5, 30)
    assert is_working_day(friday) is True
    assert is_working_day(saturday) is False
