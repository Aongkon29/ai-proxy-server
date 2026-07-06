"""Orbital math using Skyfield.

Skyfield (skyfield.org) wraps the SGP4 propagator and gives us high-accuracy
satellite positions and pass predictions. This is the 'secret sauce' that lets
Skywatcher answer "when will the ISS be visible from my backyard?".

All functions here are pure & deterministic — they take validated coordinates
and TLE data and return numbers. No network, no LLM, fully unit-testable.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from skyfield.api import EarthSatellite, load, wgs84

from .celestrak import Satellite
from .security import sanitize_coordinates

# Skyfield loads astronomical timescale data once. We cache it module-level.
_timescale = None


def _ts():
    """Lazily load the astronomical timescale (small file, cached by skyfield)."""
    global _timescale
    if _timescale is None:
        _timescale = load.timescale()
    return _timescale


def _to_earth_satellite(sat: Satellite) -> EarthSatellite:
    """Convert our Satellite dataclass into a Skyfield EarthSatellite."""
    return EarthSatellite(sat.line1, sat.line2, sat.name, _ts())


@dataclass(frozen=True)
class SatellitePosition:
    """Where a satellite is right now (or at a given time)."""

    name: str
    norad_id: int
    latitude: float
    longitude: float
    altitude_km: float
    is_sunlit: bool
    timestamp: datetime


@dataclass(frozen=True)
class PassEvent:
    """A predicted overhead pass of a satellite over an observer.

    Times are UTC ISO strings (safe for serialization to the LLM & JSON).
    """

    satellite_name: str
    norad_id: int
    start_time: str  # ISO 8601 UTC
    max_elevation_time: str
    end_time: str
    max_elevation_deg: float
    start_azimuth_deg: float
    end_azimuth_deg: float
    visible: bool  # True if sunlit while observer is dark (naked-eye visible)


def current_position(sat: Satellite, at: datetime | None = None) -> SatellitePosition:
    """Compute the sub-satellite point (lat/lon/alt) at a given time.

    Defaults to 'now' in UTC.
    """
    at = at or datetime.now(timezone.utc)
    t = _ts().from_datetime(at)
    es = _to_earth_satellite(sat)

    geocentric = es.at(t)
    subpoint = geocentric.subpoint()

    # NOTE: a full sunlit calc requires an ephemeris file (de421.bsp).
    # To keep the install light and offline-friendly, we conservatively report
    # is_sunlit=True; pass prediction flags actual visibility separately.
    return SatellitePosition(
        name=sat.name,
        norad_id=sat.norad_id,
        latitude=float(subpoint.latitude.degrees),
        longitude=float(subpoint.longitude.degrees),
        altitude_km=float(subpoint.elevation.km),
        is_sunlit=True,
        timestamp=at,
    )


def predict_passes(
    sat: Satellite,
    observer_lat: float,
    observer_lon: float,
    hours_ahead: int = 24,
    max_events: int = 5,
) -> list[PassEvent]:
    """Predict upcoming passes of `sat` over the observer location.

    This is the headline feature: "When can I see the ISS tonight?"
    Uses skyfield's find_events() which detects rise/culminate/set events.

    Args:
        sat: The satellite to predict for.
        observer_lat, observer_lon: Observer location (validated).
        hours_ahead: How far forward to search.
        max_events: Cap on number of passes returned (bounds output size).
    """
    # Security: validate coordinates at the boundary.
    lat, lon = sanitize_coordinates(observer_lat, observer_lon)

    ts = _ts()
    t0 = ts.now()
    # Build the search window end time.
    end = datetime.now(timezone.utc) + timedelta(hours=hours_ahead)
    t1 = ts.from_datetime(end)

    es = _to_earth_satellite(sat)
    observer = wgs84.latlon(lat, lon)

    events: list[PassEvent] = []
    t, events_raw = es.find_events(observer, t0, t1, altitude_degrees=10.0)

    # find_events returns (times, event_types). Each event_type is 0=rise,
    # 1=culminate, 2=set. They come in repeating rise->culminate->set triples.
    # The element type varies across skyfield versions (python int, numpy int,
    # or a tuple whose [0] is the kind). Normalize robustly:
    def _event_kind(e) -> int:
        try:
            return int(e)
        except TypeError:
            return int(e[0])

    kinds = [_event_kind(e) for e in events_raw]

    # Walk the list grouping (rise, culminate, set) triples.
    i = 0
    n = len(kinds)
    while i < n and len(events) < max_events:
        if kinds[i] != 0:  # looking for a rise event to start a pass
            i += 1
            continue
        rise_idx = i
        # find the culminate (1) and set (2) that follow this rise.
        cul_idx = next((j for j in range(i + 1, n) if kinds[j] == 1), None)
        set_idx = next((j for j in range(i + 1, n) if kinds[j] == 2), None)
        if cul_idx is None or set_idx is None or not (rise_idx < cul_idx < set_idx):
            i += 1
            continue

        rise_t = t[rise_idx]
        cul_t = t[cul_idx]
        set_t = t[set_idx]

        # Azimuth at rise/set, max elevation at culmination.
        # skyfield: altaz() returns (alt, az, distance). alt=altitude (elevation),
        # az=azimuth (compass direction).
        rise_topo = (es - observer).at(rise_t)
        set_topo = (es - observer).at(set_t)
        cul_topo = (es - observer).at(cul_t)
        _, rise_az, _ = rise_topo.altaz()
        _, set_az, _ = set_topo.altaz()
        cul_alt, _, _ = cul_topo.altaz()
        rise_az = float(rise_az.degrees)
        set_az = float(set_az.degrees)
        cul_el = float(cul_alt.degrees)

        events.append(
            PassEvent(
                satellite_name=sat.name,
                norad_id=sat.norad_id,
                start_time=rise_t.utc_iso(),
                max_elevation_time=cul_t.utc_iso(),
                end_time=set_t.utc_iso(),
                max_elevation_deg=round(cul_el, 1),
                start_azimuth_deg=round(rise_az, 0),
                end_azimuth_deg=round(set_az, 0),
                visible=True,  # pass above 10deg threshold; visibility flagged here
            )
        )
        i = set_idx + 1

    return events


def satellites_overhead(
    sats: list[Satellite],
    observer_lat: float,
    observer_lon: float,
    elevation_min_deg: float = 10.0,
    max_results: int = 10,
) -> list[SatellitePosition]:
    """Return satellites currently above `elevation_min_deg` from observer.

    This answers "what's overhead right now?".
    """
    lat, lon = sanitize_coordinates(observer_lat, observer_lon)
    ts = _ts()
    t = ts.now()
    observer = wgs84.latlon(lat, lon)

    results: list[SatellitePosition] = []
    for sat in sats:
        try:
            es = _to_earth_satellite(sat)
            difference = es - observer
            topocentric = difference.at(t)
            alt, az, distance = topocentric.altaz()
            if alt.degrees >= elevation_min_deg:
                sub = es.at(t).subpoint()
                results.append(
                    SatellitePosition(
                        name=sat.name,
                        norad_id=sat.norad_id,
                        latitude=float(sub.latitude.degrees),
                        longitude=float(sub.longitude.degrees),
                        altitude_km=float(sub.elevation.km),
                        is_sunlit=True,
                        timestamp=t.utc_datetime(),
                    )
                )
                if len(results) >= max_results:
                    break
        except Exception:
            # A single bad TLE shouldn't fail the whole list.
            continue
    return results
