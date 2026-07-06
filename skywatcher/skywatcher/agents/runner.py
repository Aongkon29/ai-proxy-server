"""Runner: execute the multi-agent system end-to-end.

Wraps ADK's Runner + InMemorySessionService so callers get a simple `ask()`
function. This is the bridge between the CLI/MCP layer and the agents.
"""
from __future__ import annotations

import asyncio
from typing import Iterator

from ..config import settings
from .specialists import _ADK_AVAILABLE


def ask(query: str, *, user_id: str = "capstone_user") -> str:
    """Send a query to the coordinator and return the final text response.

    This is the main entry point for the CLI. It:
      1. Builds the coordinator (with all sub-agents).
      2. Creates/resumes an in-memory session.
      3. Runs the query and collects the coordinator's final text.

    Args:
        query: The user's natural-language question.
        user_id: Stable user id for session continuity (default is anonymous).

    Returns:
        The agent's final textual response.
    """
    if not _ADK_AVAILABLE:
        return _fallback_response(query)
    if not settings.has_api_key:
        return (
            "Skywatcher needs an LLM API key to run the agent.\n"
            "Option A — Gemini (free, but geo-blocked in some regions):\n"
            "  Get a key at https://aistudio.google.com/apikey, then set\n"
            "  GEMINI_API_KEY in your .env file.\n"
            "Option B — DeepSeek (works globally, OpenAI-compatible):\n"
            "  Get a key at https://platform.deepseek.com, then set\n"
            "  DEEPSEEK_API_KEY in your .env file.\n\n"
            "The non-LLM tools (CelesTrak fetch, pass prediction) still work:\n"
            "  skywatcher list-sats --category visual\n"
            "  skywatcher passes 'ISS' --lat 40.0 --lon -105.3"
        )

    return asyncio.run(_ask_async(query, user_id))


async def _ask_async(query: str, user_id: str) -> str:
    """Async implementation of ask().

    ADK 2.x made create_session() and runner.run_async() coroutine-based,
    so we need an async implementation and bridge it from the sync ask().
    """
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.genai import types as genai_types

    from .coordinator import build_coordinator

    coordinator = build_coordinator()
    # Debug: show which model/provider is active
    model_info = coordinator.model
    print(f"[skywatcher] Using model: {model_info}", flush=True)
    session_service = InMemorySessionService()
    session = await session_service.create_session(
        user_id=user_id, app_name="skywatcher"
    )

    runner = Runner(
        agent=coordinator, app_name="skywatcher", session_service=session_service
    )

    # ADK events: stream them, collect the final text response.
    content = genai_types.Content(role="user", parts=[genai_types.Part(text=query)])
    final_text = ""
    async for event in runner.run_async(
        user_id=user_id, session_id=session.id, new_message=content
    ):
        # The coordinator's final answer comes as a text part.
        if event.is_final_response() and event.content and event.content.parts:
            final_text = "".join(p.text for p in event.content.parts if p.text)
            break
    return final_text or "I couldn't produce a response. Please try rephrasing."


def ask_stream(query: str, *, user_id: str = "capstone_user") -> Iterator[str]:
    """Streaming variant: yields text chunks as the agent produces them.

    Useful for the interactive CLI mode where we want live output.
    """
    if not _ADK_AVAILABLE or not settings.has_api_key:
        yield ask(query, user_id=user_id)
        return

    import queue
    import threading

    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.genai import types as genai_types

    from .coordinator import build_coordinator

    result_queue: queue.Queue = queue.Queue()

    async def _run() -> None:
        try:
            coordinator = build_coordinator()
            session_service = InMemorySessionService()
            session = await session_service.create_session(
                user_id=user_id, app_name="skywatcher"
            )
            runner = Runner(
                agent=coordinator,
                app_name="skywatcher",
                session_service=session_service,
            )
            content = genai_types.Content(
                role="user", parts=[genai_types.Part(text=query)]
            )
            async for event in runner.run_async(
                user_id=user_id, session_id=session.id, new_message=content
            ):
                if event.content and event.content.parts:
                    text = "".join(p.text for p in event.content.parts if p.text)
                    if text:
                        result_queue.put(text)
        except Exception as e:
            result_queue.put(e)
        finally:
            result_queue.put(None)  # sentinel — streaming done

    # Run the async generator in a background thread so we can yield
    # chunks synchronously to the caller.
    loop = asyncio.new_event_loop()
    thread = threading.Thread(target=lambda: loop.run_until_complete(_run()))
    thread.start()

    try:
        while True:
            item = result_queue.get()
            if item is None:
                break
            if isinstance(item, Exception):
                raise item
            yield item
    finally:
        thread.join()
        loop.close()


def _fallback_response(query: str) -> str:
    """Used when ADK isn't installed. Still routes to the tool layer directly
    so the CLI is useful for the deterministic commands."""
    return (
        "Agent layer unavailable (ADK not installed).\n"
        f"You asked: {query}\n\n"
        "Use the deterministic CLI commands instead:\n"
        "  skywatcher list-sats\n  skywatcher passes 'ISS' --lat 40.0 --lon -105.3\n"
        "  skywatcher overhead --lat 40.0 --lon -105.3\n"
        "Install agent deps: pip install google-adk google-genai"
    )
