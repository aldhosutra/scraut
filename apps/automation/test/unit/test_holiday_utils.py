"""test/unit/test_holiday_utils.py — holiday utility unit tests"""
import json
import pytest
from datetime import date
from pathlib import Path
from unittest.mock import patch, MagicMock

from scraut.platform.utils.holiday_utils import (
    get_public_holidays, get_all_holidays, is_holiday, clear_cache,
)
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
