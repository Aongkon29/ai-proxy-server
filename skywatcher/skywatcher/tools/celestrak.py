"""CelesTrak TLE fetcher.

CelesTrak (celestrak.org) publishes Two-Line Element sets for free, no API key.
We fetch TLEs for satellite categories, cache them briefly (they update ~every 2h),
and expose a clean Python API.

A TLE looks like:
    NOAA 15
    1 25333U 98030A   24123.50000000  .00000040  00000-0  11659-4 0  9991
    2 25333  98.6200 350.0000 0123456  45.0000 315.0000 14.25000000 12345

The numbers encode the orbit precisely enough to propagate position via SGP4.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Iterator

import httpx

from ..config import settings
from .security import celestrak_limiter

# CelesTrak endpoints. These are public, free, no auth.
_BASE = "https://celestrak.org/NORAD/elements/gp.php?FORMAT=json"
# Categories we care about. Each is a well-known CelesTrak group.
CATEGORIES = {
    "stations": "Space stations & large satellites (ISS, Tiangong, Hubble)",
    "active": "All active satellites",
    "starlink": "Starlink constellation",
    "geo": "Geostationary satellites",
    "visual": "Bright/naked-eye visible satellites (best for stargazing)",
    "last-30-days": "Satellites launched in the last 30 days",
    "science": "Scientific satellites",
    "weather": "Weather satellites",
    "amateur": "Amateur radio satellites",
}


@dataclass(frozen=True)
class Satellite:
    """A satellite with its orbital elements.

    Frozen so instances are hashable & safe to share between agents.
    """

    name: str
    norad_id: int
    line1: str
    line2: str

    @property
    def tle(self) -> str:
        """Full 3-line TLE string."""
        return f"{self.name}\n{self.line1}\n{self.line2}"


# --- Fetching --------------------------------------------------------------

# In-memory cache with TTL. TLEs drift, so we never cache longer than this.
_CACHE_TTL_SECONDS = 2 * 60 * 60  # 2 hours — matches CelesTrak's update cadence
_cache: dict[str, tuple[float, list[Satellite]]] = {}


def _fetch_raw(category: str) -> list[Satellite]:
    """Fetch a category from CelesTrak and parse into Satellite objects.

    Uses the JSON GP format which is much easier to parse than raw 3-line TLEs.
    """
    url = f"{_BASE}&GROUP={category}"
    # Respect CelesTrak's fair-use policy via the shared rate limiter.
    if not celestrak_limiter.acquire():
        raise RuntimeError(
            "CelesTrak rate limit reached. Please wait a minute and retry."
        )

    resp = httpx.get(url, timeout=settings.celestrak_timeout, follow_redirects=True)
    resp.raise_for_status()

    data = resp.json()
    sats: list[Satellite] = []
    for entry in data:
        # The GP JSON format uses OBJECT_NAME, NORAD_CAT_ID, and a GP sub-object.
        name = entry.get("OBJECT_NAME", "UNKNOWN")
        norad = int(entry.get("NORAD_CAT_ID", 0))
        gp = entry.get("GP", entry)  # support both flat and nested shapes
        line1 = gp.get("TLE_LINE1", "")
        line2 = gp.get("TLE_LINE2", "")
        if line1 and line2:
            sats.append(Satellite(name=name, norad_id=norad, line1=line1, line2=line2))
    return sats


def get_satellites(category: str = "visual") -> list[Satellite]:
    """Get satellites for a category, with TTL caching.

    Defaults to 'visual' (bright satellites good for stargazing) because that's
    what most users want. Use 'last-30-days' for recently launched sats.
    """
    if category not in CATEGORIES:
        raise ValueError(
            f"Unknown category '{category}'. Valid: {sorted(CATEGORIES)}"
        )

    now = time.time()
    cached = _cache.get(category)
    if cached and (now - cached[0]) < _CACHE_TTL_SECONDS:
        return cached[1]

    sats = _fetch_raw(category)
    _cache[category] = (now, sats)
    return sats


def find_satellite(name_or_id: str, category: str = "active") -> Satellite | None:
    """Find a single satellite by name (case-insensitive substring) or NORAD id.

    Searches the given category plus 'last-30-days' for recent launches.
    Returns None if not found.
    """
    needle = name_or_id.strip().lower()
    try:
        norad = int(needle)
    except ValueError:
        norad = None

    for cat in (category, "last-30-days", "visual", "active"):
        try:
            for sat in get_satellites(cat):
                if norad is not None and sat.norad_id == norad:
                    return sat
                if needle and needle in sat.name.lower():
                    return sat
        except Exception:
            # Network errors shouldn't crash the whole search — try next category.
            continue
    return None


def list_categories() -> dict[str, str]:
    """Return the catalog of available categories with human descriptions."""
    return dict(CATEGORIES)


def iter_all(category: str = "active") -> Iterator[Satellite]:
    """Iterator over satellites in a category (memory-friendly for big groups)."""
    yield from get_satellites(category)
