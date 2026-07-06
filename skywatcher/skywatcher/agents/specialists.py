"""Specialist sub-agents for Skywatcher.

Each sub-agent owns one capability and exposes the tools it needs. The
coordinator delegates to them via ADK's sub-agent mechanism.
"""
from __future__ import annotations

from ..config import settings
from ..tools import celestrak, sky_math
from ..tools.security import sanitize_coordinates, sanitize_text

# ADK is the framework taught in the course. We import lazily so the package
# can still be imported (and the non-LLM tools tested) on machines without ADK.
try:
    from google.adk.agents import Agent
    from google.adk.tools import FunctionTool

    _ADK_AVAILABLE = True
except Exception:  # pragma: no cover - fallback path
    _ADK_AVAILABLE = False

    class _AgentShim:
        """Minimal stand-in so module import never fails without ADK.

        Real ADK is required for the agent to actually run; this just lets
        `import skywatcher.agents` succeed for tool-level testing.
        """

        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    Agent = _AgentShim  # type: ignore

    class FunctionTool:  # type: ignore
        """Fallback: just stores the function so Agent(tools=...) still works."""

        def __init__(self, func):
            self.func = func

        def __call__(self, *a, **k):
            return self.func(*a, **k)


# ===========================================================================
# Tool functions (the deterministic capabilities each agent can call).
# These are PLAIN functions — ADK auto-wraps them into FunctionTools when passed
# to Agent(tools=[...]). Type hints become the JSON schema the LLM sees.
# ===========================================================================


def list_satellite_categories() -> dict:
    """Return the catalog of satellite categories you can query."""
    return celestrak.list_categories()


def fetch_satellites(category: str = "visual") -> list[dict]:
    """Fetch satellites in a CelesTrak category.

    Use 'visual' for bright naked-eye satellites, 'starlink' for the Starlink
    constellation, 'last-30-days' for recently launched satellites.
    Returns name + NORAD id for each (capped at 60 to bound context).
    """
    sats = celestrak.get_satellites(category)
    return [{"name": s.name, "norad_id": s.norad_id} for s in sats[:60]]


def lookup_satellite(query: str) -> dict | None:
    """Find a satellite by name (e.g. 'ISS', 'Hubble') or NORAD id ('25544')."""
    # Sanitize the free-text query before using it (security feature).
    query = sanitize_text(query)
    sat = celestrak.find_satellite(query)
    if sat is None:
        return None
    return {"name": sat.name, "norad_id": sat.norad_id}


def predict_passes(
    satellite_query: str, observer_lat: float, observer_lon: float, hours_ahead: int = 24
) -> list[dict]:
    """Predict when a satellite will pass over an observer location.

    Call this to answer 'When can I see the ISS tonight?'. Times are UTC ISO.
    Returns passes with start/max/end times, max elevation in degrees, and
    rise/set azimuth in degrees.
    """
    # Validate coordinates at the trust boundary.
    observer_lat, observer_lon = sanitize_coordinates(observer_lat, observer_lon)
    satellite_query = sanitize_text(satellite_query)

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


def overhead_now(observer_lat: float, observer_lon: float) -> list[dict]:
    """List bright satellites currently above the horizon (>10 deg) from a location."""
    observer_lat, observer_lon = sanitize_coordinates(observer_lat, observer_lon)
    sats = celestrak.get_satellites("visual")
    positions = sky_math.satellites_overhead(sats, observer_lat, observer_lon)
    return [
        {
            "name": p.name,
            "norad_id": p.norad_id,
            "altitude_km": round(p.altitude_km, 1),
        }
        for p in positions
    ]


# ===========================================================================
# Agent definitions
# ===========================================================================

# Instruction for the satellite-data agent: it knows how to find satellites.
_SATELLITE_DATA_INSTRUCTION = """You are the Satellite Data specialist in the Skywatcher team.
Your job: look up satellites by name or NORAD id, and list satellites by category.

When you get a request:
1. If the user names a satellite, call lookup_satellite. Try common variants
   (e.g. 'ISS' -> also try 'SPACE STATION', '25544').
2. If the user wants to browse, call fetch_satellites with an appropriate
   category. Use 'last-30-days' for 'recently launched' queries.
3. Report the satellite name and NORAD id back to the coordinator.

Be concise. You are a specialist; hand control back after answering."""

# Instruction for the sky-math agent: it predicts passes & overhead sats.
_SKY_MATH_INSTRUCTION = """You are the Sky Math specialist in the Skywatcher team.
Your job: predict satellite passes and list what's overhead right now.

When you get a request:
1. For 'when can I see X' questions, call predict_passes. You NEED the
   observer's latitude and longitude. If the user gave a city name, ask the
   coordinator (do not guess). If no location at all, use the default location.
2. For 'what's overhead now' questions, call overhead_now with the location.
3. Convert UTC times to a human-friendly form. Mention the max elevation in
   degrees and the compass direction of the rise (0=N, 90=E, 180=S, 270=W).

Report a short, scannable summary of passes back to the coordinator."""

# Instruction for the educator agent: general space Q&A, no tools.
_EDUCATOR_INSTRUCTION = """You are the Educator specialist in the Skywatcher team.
Your job: answer general questions about satellites, orbits, and space.

You have NO tools — rely on your training knowledge. Be accurate and engaging.
If a question requires live data (e.g. 'where is the ISS right now?'), tell
the coordinator to route it to the Sky Math or Satellite Data agent instead.

Keep answers focused: a few sentences for simple questions, a short paragraph
for complex ones. Avoid speculation; if you're unsure, say so."""


def build_satellite_data_agent(model) -> "Agent":
    """The agent that finds & lists satellites."""
    return Agent(
        name="satellite_data",
        model=model,
        instruction=_SATELLITE_DATA_INSTRUCTION,
        tools=[list_satellite_categories, fetch_satellites, lookup_satellite],
    )


def build_sky_math_agent(model) -> "Agent":
    """The agent that predicts passes & overhead satellites.

    NOTE: in a full deployment this agent would consume its tools via MCP
    (see skywatcher.mcp_server). Here we bind them directly as function_tools
    so the agent works without a separate MCP process. The MCP server is
    demonstrated separately and is 100% API-compatible with these functions.
    """
    return Agent(
        name="sky_math",
        model=model,
        instruction=_SKY_MATH_INSTRUCTION,
        tools=[predict_passes, overhead_now],
    )


def build_educator_agent(model) -> "Agent":
    """The agent that answers general space questions (no tools)."""
    return Agent(
        name="educator",
        model=model,
        instruction=_EDUCATOR_INSTRUCTION,
        tools=[],
    )
