# Skywatcher: A Multi-Agent Companion for What's Overhead

**Track:** Freestyle
**Tagline:** Turn "is there anything cool in the sky tonight?" into a real orbital calculation.

---

## The Problem

There are over 10,000 active satellites orbiting Earth — the ISS, Hubble,
growing Starlink trains, and newly launched missions every week. Yet answering
the simple question *"when can I actually see one from my backyard tonight?"*
still means digging through terse astronomy tables, copying NORAD catalog
numbers, pasting coordinates, and doing mental math on azimuths and elevations.

The data is free and public. The friction is in the translation layer between
raw orbital elements and a curious human. That friction is exactly the kind of
problem a small team of AI agents is good at removing: one agent understands
the question, another fetches the right data, another does the math, and a
third explains the result in plain language.

## The Solution

**Skywatcher** is a multi-agent system that takes plain-English questions about
satellites and returns real, computed answers — not hallucinations. Ask *"When
can I see the ISS from Boulder?"* and the system:

1. Routes the question to a specialist agent,
2. Fetches the ISS's live orbital elements (TLE) from CelesTrak,
3. Propagates the orbit with Skyfield/SGP4 to find rise/culminate/set events,
4. Reports the next visible passes with times, elevation, and compass direction.

Crucially, the agent **never invents satellite data**. Every number — position,
pass time, azimuth — comes from a deterministic tool that does real orbital
mechanics. The LLM only orchestrates and narrates. This is the design principle
that makes Skywatcher trustworthy: *the agent reasons in language, but it
calculates in code.*

## Architecture

Skywatcher is a **coordinator + 3 specialist sub-agents** built on Google's
Agent Development Kit (ADK):

```
            ┌──────────────────────────────┐
            │     Coordinator (root)       │
            │  routes request to a specialist  │
            └──────┬──────────┬──────────┬──────┘
                   │          │          │
        ┌──────────▼─┐  ┌─────▼──────┐  ┌▼───────────┐
        │ Satellite   │  │ Sky Math   │  │ Educator    │
        │ Data Agent  │  │ Agent      │  │ Agent       │
        │ find / list │  │ passes /   │  │ general     │
        │ satellites  │  │ overhead   │  │ space Q&A   │
        └──────┬──────┘  └─────┬──────┘  └─────────────┘
               │               │
        function tools    function tools
               │               │
        ┌──────▼───────────────▼──────┐    ┌──────────────────┐
        │  Deterministic Tool Layer   │◄──►│   MCP Server     │
        │  CelesTrak fetch · Skyfield │    │ (same tools,     │
        │  SGP4 math · security       │    │  over MCP)       │
        └──────────────┬──────────────┘    └──────────────────┘
                       │
                CelesTrak (free, no key)
```

| Agent | Responsibility | Tools |
|-------|----------------|-------|
| **Coordinator** | Decides which specialist handles the request | none — delegates |
| **Satellite Data** | Find satellites by name/NORAD id, list by category | 3 function tools |
| **Sky Math** | Predict visible passes, list what's overhead now | 2 function tools |
| **Educator** | Answer general questions about orbits and space | none (LLM knowledge) |

**Why multi-agent?** Each agent gets a small, focused prompt and only the tools
it needs. The Sky Math agent can't waste tokens browsing satellite lists; the
Satellite Data agent can't accidentally try to do orbital math. The coordinator
keeps the user-facing conversation coherent. This separation makes the system
cheaper, more reliable, and easier to debug than a single mega-prompted agent.

**The tool layer** is deliberately separate from the agent layer. It lives in
`skywatcher/tools/` and is fully unit-testable without an API key or even
internet (tests use a synthetic TLE). This is what guarantees correctness: the
orbital math is deterministic code, not LLM output.

## Course Concepts Demonstrated

The capstone requires at least **3** of 6 course concepts. Skywatcher
demonstrates **all 6**:

1. **Agent / Multi-agent system (ADK)** — `skywatcher/agents/`. A root
   coordinator delegates to three sub-agents via ADK's `sub_agents` mechanism.
   Each sub-agent is a full `google.adk.agents.Agent` with its own instruction
   and tools.

2. **MCP Server** — `skywatcher/mcp_server/server.py`. A FastMCP server exposes
   five tools (`list_categories`, `get_satellites`, `find_satellite`,
   `predict_visible_passes`, `whats_overhead`) plus a default-location
   resource. Run with `skywatcher mcp serve` and any MCP client (Claude
   Desktop, Antigravity, Cursor) can call them. The agent layer and the MCP
   server share the *same* underlying tool functions — proving the tools are
   genuinely reusable across clients.

3. **Antigravity** — The project was developed and run inside the Antigravity
   IDE; the demo video shows the agent running there.

4. **Security features** — `skywatcher/tools/security.py`. Three concrete
   defenses: (a) coordinate validation at the trust boundary (range-checked,
   NaN/inf-rejected), (b) text sanitization (control-char stripping, length
   caps, prompt-injection heuristics), (c) rate limiting on outbound CelesTrak
   calls. Plus env-only secrets and no PII persistence — sessions are
   in-memory and locations are used ephemerally.

5. **Deployability** — `Dockerfile` + `docker-compose.yml`. A reproducible
   container image: `docker build -t skywatcher . && docker run -e
   GEMINI_API_KEY=... skywatcher ask "..."`. The video demonstrates this.

6. **Agent skills (CLI)** — `skywatcher/cli.py`. A `click`-based CLI with
   subcommands `ask`, `passes`, `overhead`, `list-sats`, `find`, and `mcp
   serve`. Deterministic commands work with no API key; `ask` invokes the full
   multi-agent system.

## Implementation Highlights

**Data source — CelesTrak.** Orbital elements are published as Two-Line
Element sets (TLEs), free and key-less. `celestrak.py` fetches the JSON GP
format, caches for 2 hours (CelesTrak's own update cadence), and rate-limits to
≤20 calls/min to respect fair-use.

**Orbital math — Skyfield.** `sky_math.py` wraps Skyfield's `EarthSatellite`,
which uses the SGP4 propagator (the standard for LEO orbit prediction).
`find_events()` detects rise/culminate/set events above a 10° elevation
threshold; we extract max elevation and rise/set azimuth for each pass. This is
the same math that powers professional tracking apps.

**Tool reuse across surfaces.** The same five functions back three surfaces:
the ADK agents (as function tools), the MCP server (as `@mcp.tool()`), and the
CLI (called directly). One implementation, three integration patterns.

**Graceful degradation.** The package imports and the deterministic CLI
commands work *without* `google-adk` or a Gemini key — the agent layer is
imported lazily and falls back to a helpful message. This makes the tool layer
testable in CI with zero credentials.

## Verification

- **14 unit tests** pass offline (synthetic TLE, no API key, no internet),
  covering security validators and orbital math.
- The full multi-agent system builds with real ADK: coordinator +
  `satellite_data` (3 tools) + `sky_math` (2 tools) + `educator` (0 tools).
- The MCP server loads and registers all five tools.
- Docker image builds and runs end-to-end.

## Project Journey

I started by asking what would make a *good* freestyle project — something
genuinely useful, demoable in five minutes, and a natural fit for the course
concepts. Satellite tracking hit all three: real free data, a real calculation
the LLM can't do reliably on its own (so tools genuinely matter), and a visible
"wow" moment when a pass prediction lands.

The first working version was a single mega-agent with all tools bolted on. It
worked, but the prompt was bloated and the agent would sometimes call the wrong
tool. Splitting into a coordinator + specialists immediately improved
reliability — each sub-agent's prompt shrank to a few focused lines, and
routing became predictable.

The hardest bug was in the orbital math: Skyfield's `find_events` returns event
types whose type varies across versions (Python int, numpy int, or tuple),
which broke naive indexing. I normalized them robustly with a `try: int(e)
except: int(e[0])` helper. A second bug — calling `.az()` instead of
`.altaz()` — reminded me why the tool layer must be unit-tested separately
from the LLM.

The security layer came from asking "what could a malicious user send?" Bad
coordinates could produce nonsense; oversized text could blow up token usage;
prompt-injection phrases could try to exfiltrate the system prompt. None are
fully solvable, but each gets a concrete, defense-in-depth mitigation.

## What's Next

- Add weather integration (a pass is useless behind clouds) via Open-Meteo.
- Detect sunlit-vs-eclipsed passes using a Skyfield ephemeris for true
  naked-eye visibility.
- Persistent per-user location with explicit consent (currently stateless).

## Running It

Full setup takes under two minutes:

```bash
git clone <repo> skywatcher && cd skywatcher
pip install -e .
cp .env.example .env  # add your free GEMINI_API_KEY
skywatcher ask "When can I see the ISS from London?"
```

Or with Docker: `docker run -e GEMINI_API_KEY=... skywatcher ask "..."`

See the [README](.) for full documentation, the [architecture diagram](docs/architecture.svg),
and the test suite (`pytest -q`).

---

*Built for the Kaggle × Google 5-Day AI Agents Capstone. No API keys are
included in the codebase. All satellite data comes from the free, public
CelesTrak service.*
