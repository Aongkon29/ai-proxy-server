"""Skywatcher MCP server.

Exposes the satellite-data tools over the Model Context Protocol so that any
MCP-compatible client (Claude Desktop, Antigravity, Cursor, or our own ADK
agents) can discover and call them.

Run standalone:
    python -m skywatcher.mcp_server.server
    # or: skywatcher mcp serve

The MCP SDK's FastMCP makes this ~50 lines: define functions, decorate them
with @mcp.tool(), and call mcp.run(). The protocol handles JSON-RPC framing,
tool discovery, and schema generation for the LLM.
"""
from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from ..config import settings
from ..tools import celestrak, sky_math
from ..tools.security import sanitize_coordinates

# Create the MCP server. The name is what clients see in tool-discovery UI.
mcp = FastMCP("skywatcher")


# --- Tools -----------------------------------------------------------------


@mcp.tool()
def list_categories() -> dict[str, str]:
    """List the satellite categories you can query (e.g. 'visual', 'starlink').

    Returns a mapping of category id -> human description.
    """
    return celestrak.list_categories()


@mcp.tool()
def get_satellites(category: str = "visual") -> list[dict]:
    """Fetch satellites in a CelesTrak category.

    Args:
        category: One of the keys from list_categories(). Default 'visual'
                  (bright, naked-eye-visible satellites — best for stargazing).

    Returns:
        A list of {name, norad_id} for each satellite. TLE lines are omitted
        to keep the payload small for the LLM context window.
    """
    sats = celestrak.get_satellites(category)
    return [{"name": s.name, "norad_id": s.norad_id} for s in sats[:60]]


@mcp.tool()
def find_satellite(query: str) -> dict | None:
    """Find a single satellite by name or NORAD id.

    Args:
        query: Satellite name (e.g. 'ISS', 'Hubble', 'STARLINK-1234') or
               NORAD catalog number (e.g. '25544' for the ISS).

    Returns:
        {name, norad_id} or null if not found.
    """
    sat = celestrak.find_satellite(query)
    if sat is None:
        return None
    return {"name": sat.name, "norad_id": sat.norad_id}


@mcp.tool()
def predict_visible_passes(
    satellite_query: str,
    observer_lat: float,
    observer_lon: float,
    hours_ahead: int = 24,
) -> list[dict]:
    """Predict when a satellite will be visible from a location.

    This is the headline feature: 'When can I see the ISS tonight?'

    Args:
        satellite_query: Satellite name or NORAD id (e.g. 'ISS' or '25544').
        observer_lat: Observer latitude in decimal degrees (-90..90).
        observer_lon: Observer longitude in decimal degrees (-180..180).
        hours_ahead: How far ahead to search (default 24h).

    Returns:
        List of passes with start/max/end times (UTC ISO 8601), max elevation
        in degrees, and rise/set azimuth in degrees.
    """
    # Validate coordinates at the trust boundary (security feature).
    observer_lat, observer_lon = sanitize_coordinates(observer_lat, observer_lon)

    sat = celestrak.find_satellite(satellite_query)
    if sat is None:
        return []

    passes = sky_math.predict_passes(sat, observer_lat, observer_lon, hours_ahead)
    return [
        {
            "satellite": p.satellite_name,
            "start_utc": p.start_time,
            "max_elevation_utc": p.max_elevation_time,
            "end_utc": p.end_time,
            "max_elevation_deg": p.max_elevation_deg,
            "rise_azimuth_deg": p.start_azimuth_deg,
            "set_azimuth_deg": p.end_azimuth_deg,
        }
        for p in passes
    ]


@mcp.tool()
def whats_overhead(
    observer_lat: float, observer_lon: float, max_results: int = 10
) -> list[dict]:
    """List satellites currently overhead (>10deg elevation) from a location.

    Args:
        observer_lat: Observer latitude (-90..90).
        observer_lon: Observer longitude (-180..180).
        max_results: Max number of satellites to return.

    Returns:
        List of {name, norad_id, latitude, longitude, altitude_km} for each
        satellite currently above the horizon from the observer's location.
    """
    observer_lat, observer_lon = sanitize_coordinates(observer_lat, observer_lon)

    # Use the 'visual' category — these are the bright ones users can actually see.
    sats = celestrak.get_satellites("visual")
    positions = sky_math.satellites_overhead(
        sats, observer_lat, observer_lon, max_results=max_results
    )
    return [
        {
            "name": p.name,
            "norad_id": p.norad_id,
            "latitude": round(p.latitude, 3),
            "longitude": round(p.longitude, 3),
            "altitude_km": round(p.altitude_km, 1),
        }
        for p in positions
    ]


# --- Resource: default observer location -----------------------------------


@mcp.resource("skywatcher://default-location")
def default_location() -> str:
    """The default observer location (latitude, longitude) used when the user
    doesn't provide one. Configurable via env vars DEFAULT_LAT / DEFAULT_LON.
    """
    return f"{settings.default_lat}, {settings.default_lon}"


# --- Entrypoint ------------------------------------------------------------


def main() -> None:
    """Run the MCP server on stdio (the standard MCP transport)."""
    mcp.run()


if __name__ == "__main__":
    main()
