"""
platform/utils/holiday_utils.py
Merge public holidays from Nager.Date API with team-configured overrides.

Two sources:
  API  — https://date.nager.at/api/v3/PublicHolidays/{year}/{countryCode}
         Free, no API key, 100+ countries. Results cached in
         .scraut/holidays/{CC}/{YEAR}.json so the network is only hit once per
         country/year combination.
  File — config holidays.extra_dates / holidays.skip_dates (YYYY-MM-DD lists)
         extra_dates adds company-specific days not covered by the API.
         skip_dates removes API-provided dates your team works anyway.

Merged rule: (api_holidays | extra_dates) - skip_dates
"""
import json
import logging
import urllib.request
import urllib.error
from datetime import date
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_NAGER_URL = "https://date.nager.at/api/v3/PublicHolidays/{year}/{country}"

# In-process cache so multiple calls in the same script run don't repeat I/O
_cache: dict[tuple, set[date]] = {}


def _cache_path(scraut_root: Path, country_code: str, year: int) -> Path:
    return scraut_root / "holidays" / country_code.upper() / f"{year}.json"


def _fetch_nager(year: int, country_code: str) -> list[str]:
    """Fetch holiday date strings from Nager.Date. Returns [] on any failure."""
    url = _NAGER_URL.format(year=year, country=country_code.upper())
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            data = json.loads(resp.read().decode())
        return [h["date"] for h in data if "date" in h]
    except urllib.error.HTTPError as e:
        if e.code == 404:
            logger.warning(f"No holiday data for country code {country_code!r} (404)")
        else:
            logger.warning(f"Nager.Date returned HTTP {e.code} for {country_code}/{year}")
        return []
    except Exception as e:
        logger.warning(f"Could not fetch holidays for {country_code}/{year}: {e}")
        return []


def get_public_holidays(year: int, country_code: str,
                        scraut_root: Optional[Path] = None) -> set[date]:
    """Return public holidays for year/country_code.

    Reads from .scraut/holidays cache if available; falls back to Nager.Date
    API and writes the result to cache for future runs.
    """
    key = (year, country_code.upper())
    if key in _cache:
        return _cache[key]

    date_strings: list[str] = []

    if scraut_root:
        cache_file = _cache_path(scraut_root, country_code, year)
        if cache_file.exists():
            try:
                date_strings = json.loads(cache_file.read_text())
                logger.debug(f"Loaded {len(date_strings)} holidays from cache: {cache_file}")
            except Exception as e:
                logger.warning(f"Corrupt holiday cache at {cache_file}: {e}")
                date_strings = []

    if not date_strings:
        date_strings = _fetch_nager(year, country_code)
        if date_strings and scraut_root:
            try:
                cache_file = _cache_path(scraut_root, country_code, year)
                cache_file.parent.mkdir(parents=True, exist_ok=True)
                cache_file.write_text(json.dumps(date_strings))
                logger.debug(f"Cached {len(date_strings)} holidays → {cache_file}")
            except Exception as e:
                logger.warning(f"Could not write holiday cache: {e}")

    result: set[date] = set()
    for d_str in date_strings:
        try:
            result.add(date.fromisoformat(d_str))
        except ValueError:
            logger.warning(f"Skipping invalid holiday date: {d_str!r}")

    _cache[key] = result
    return result


def get_all_holidays(year: int, config: dict,
                     scraut_root: Optional[Path] = None) -> set[date]:
    """Return the merged holiday set for `year` given config.

    Result = (api_holidays | extra_dates) - skip_dates
    """
    holiday_cfg = config.get("holidays") or {}
    holidays: set[date] = set()

    country_code = (holiday_cfg.get("country_code") or "").strip()
    if country_code:
        holidays |= get_public_holidays(year, country_code, scraut_root)

    for raw in holiday_cfg.get("extra_dates") or []:
        try:
            holidays.add(date.fromisoformat(str(raw)))
        except ValueError:
            logger.warning(f"Invalid extra_date {raw!r} — expected YYYY-MM-DD")

    for raw in holiday_cfg.get("skip_dates") or []:
        try:
            holidays.discard(date.fromisoformat(str(raw)))
        except ValueError:
            logger.warning(f"Invalid skip_date {raw!r} — expected YYYY-MM-DD")

    return holidays


def is_holiday(d: date, config: dict,
               scraut_root: Optional[Path] = None) -> bool:
    """Return True if d is in the merged holiday set for its year."""
    return d in get_all_holidays(d.year, config, scraut_root)


def clear_cache() -> None:
    """Clear the in-process holiday cache (used in tests)."""
    _cache.clear()
