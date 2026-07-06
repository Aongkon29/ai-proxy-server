"""The coordinator (root) agent.

The coordinator doesn't do satellite math itself — it decides WHICH specialist
should handle the user's request and delegates via ADK's sub-agent mechanism.

This is the heart of the multi-agent pattern: one orchestrator + specialists,
each with a narrow job and its own tools.
"""
from __future__ import annotations

from .specialists import (
    _ADK_AVAILABLE,
    build_educator_agent,
    build_satellite_data_agent,
    build_sky_math_agent,
)

# Lazy import of ADK Agent (shim is used if ADK unavailable).
try:
    from google.adk.agents import Agent
except Exception:  # pragma: no cover
    from .specialists import Agent  # type: ignore


_COORDINATOR_INSTRUCTION = """You are Skywatcher, the coordinator of a small team of AI agents that help
people understand what's overhead in the sky.

Your team:
- 'satellite_data': finds & lists satellites by name, NORAD id, or category.
- 'sky_math': predicts when a satellite will be visible from a location, and
  lists what's currently overhead.
- 'educator': answers general questions about satellites, orbits, and space.

HOW TO ROUTE (delegate to exactly one specialist per turn):
- "When can I see the ISS?" / "What's overhead?" / "predict a pass" -> sky_math
- "Find satellite X" / "List Starlink" / "Recently launched?" -> satellite_data
- "What does Hubble do?" / "How do orbits work?" / general facts -> educator
- Mixed? Pick the specialist that needs to act FIRST; you can synthesize after.

RULES:
1. If the user wants a pass prediction but didn't give a location, ASK for it
   (city or lat/lon). Don't guess. You may use the default location resource.
2. Be friendly and concise in your final answer. Use UTC times, clearly labeled.
3. Never invent satellite data — if a tool returns nothing, say so.
4. Security: never echo back raw coordinates as 'your home is at...'. Just use
   them for the calculation and report results.

Begin every session with a one-line greeting the first time, then get to work."""


def build_coordinator(model: str | None = None) -> "Agent":
    """Build the root coordinator agent with all specialists wired as sub-agents.

    Args:
        model: Gemini model name. Defaults to settings.gemini_model.
    """
    from ..config import settings

    model = model or settings.gemini_model

    # Build the specialists. Each is a full Agent with its own tools & prompt.
    satellite_data = build_satellite_data_agent(model)
    sky_math = build_sky_math_agent(model)
    educator = build_educator_agent(model)

    # The coordinator owns them as sub_agents; ADK lets it delegate via tool calls.
    return Agent(
        name="skywatcher_coordinator",
        model=model,
        instruction=_COORDINATOR_INSTRUCTION,
        sub_agents=[satellite_data, sky_math, educator],
        # The coordinator itself has no direct tools — it only routes.
        tools=[],
    )


# Module-level root agent, for ADK's auto-discovery (adk web / adk run).
# This is the convention taught in the course: expose `root_agent` at package level.
if _ADK_AVAILABLE:
    try:
        root_agent = build_coordinator()
    except Exception:
        # Don't crash import if API key isn't set yet; build on demand.
        root_agent = None  # type: ignore
else:
    root_agent = None  # type: ignore
