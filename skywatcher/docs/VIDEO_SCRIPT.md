# Skywatcher — 5-Minute Video Script

**Length target:** 4:30–5:00 · **Format:** screencast + voiceover · **Upload to:** YouTube (unlisted or public)

> Tips before recording: run `skywatcher ask "When can I see the ISS from Boulder?"`
> once *before* filming so the TLE cache is warm and the response is fast. Have
> the architecture SVG open in a browser tab. Speak naturally — one or two
> takes is fine.

---

## [0:00–0:30] Hook & Problem

**On screen:** Night sky photo / a satellite streaking overhead.

**Voiceover:**
> "There are over ten thousand active satellites orbiting Earth right now —
> the ISS, Hubble, Starlink trains, new launches every week. But if I want to
> know *when I can actually see one tonight*, I'm stuck digging through terse
> astronomy tables and doing azimuth math by hand.
>
> I'm building **Skywatcher** — an AI agent that turns plain-English questions
> into real orbital calculations. Let me show you."

---

## [0:30–1:15] Live Demo — the "wow" moment

**On screen:** Terminal. Type the command live.

**Voiceover:**
> "Here's the agent. I'll ask it a question in plain English:"
>
> *(type)* `skywatcher ask "When can I see the ISS from Boulder?"`
>
> "Behind the scenes, a coordinator agent routes this to a specialist, which
> fetches the ISS's live orbital elements from CelesTrak and propagates the
> orbit with Skyfield to find visible passes. A few seconds later:"

**On screen:** Show the agent's response (the predicted passes with times,
elevation, and compass direction).

> "Two passes in the next 24 hours — the best one tonight at 9:14 PM UTC,
> rising in the southwest and peaking almost directly overhead. That's a real
> calculation, not the LLM guessing."

---

## [1:15–2:15] Architecture

**On screen:** `docs/architecture.svg` (open in browser, zoom in).

**Voiceover:**
> "Here's how it works. Skywatcher is a **multi-agent system** built on Google's
> Agent Development Kit. A **coordinator agent** receives my question and
> routes it to one of three specialists:
>
> - the **Satellite Data** agent finds and lists satellites,
> - the **Sky Math** agent predicts passes and what's overhead,
> - the **Educator** agent answers general space questions.
>
> Each specialist only has the tools it needs, so prompts stay small and
> routing is predictable. The key design choice: the agent *reasons* in
> language, but it *calculates* in code. Every number comes from a
> deterministic tool layer that does real SGP4 orbital math."

---

## [2:15–3:15] Course Concepts

**On screen:** A bulleted list appearing as you say each one.

**Voiceover:**
> "The project demonstrates all six course concepts.
>
> **One — multi-agent ADK.** The coordinator plus three sub-agents you just saw.
>
> **Two — MCP server.** The same five tools are exposed as an MCP server, so
> any MCP client — Claude Desktop, Antigravity, Cursor — can call them."

**On screen:** Brief shot of `skywatcher mcp serve` running, or the
`server.py` file with the `@mcp.tool()` decorators.

> "**Three — Antigravity.** I built and ran this whole project inside the
> Antigravity IDE — here it is."
>
> *(show Antigravity IDE window with the code)*
>
> "**Four — security.** Coordinates are validated at the trust boundary, user
> text is sanitized and length-capped, outbound calls are rate-limited, and no
> personal data is ever stored."
>
> *(briefly show `security.py`)*
>
> "**Five — deployability.** It ships as a Docker image — one command to run
> the agent anywhere."

**On screen:** `docker run -e GEMINI_API_KEY=... skywatcher ask "..."`

> "**Six — agent skills, the CLI.** The `skywatcher` command gives you both
> the natural-language agent and deterministic subcommands — `passes`,
> `overhead`, `list-sats` — that work even without an API key."

---

## [3:15–4:00] A second demo — deterministic + MCP

**On screen:** Terminal.

**Voiceover:**
> "Here's the deterministic side — no API key needed:"

*(type)*
```
skywatcher list-sats -c last-30-days
skywatcher passes "ISS" --lat 51.5 --lon -0.12 --hours 48
```

> "That's recently launched satellites, and ISS passes over London. Every result
> is computed locally from real orbital elements."

---

## [4:00–4:40] The Build & What I Learned

**On screen:** A few lines of `sky_math.py` (the `predict_passes` function).

**Voiceover:**
> "I built this in Python with Google ADK, Skyfield for orbital mechanics, and
> CelesTrak for free TLE data. The biggest lesson: **keep the deterministic
> tool layer separate from the LLM**. Because the math is pure code with unit
> tests, I can trust every number the agent reports. The LLM only orchestrates
> and narrates — it never invents satellite data.
>
> The hardest bug was Skyfield's `find_events` returning event types in
> different shapes across versions — a reminder that even 'just call a
> library' code needs tests."

---

## [4:40–5:00] Close

**On screen:** GitHub URL + "Skywatcher" title card.

**Voiceover:**
> "Skywatcher turns curiosity about the sky into a real answer in seconds.
> Full code, tests, and setup instructions are on GitHub — link in the
> description. Thanks for watching, and clear skies."

---

## Recording checklist

- [ ] Warm the TLE cache: run `skywatcher list-sats -c visual` before filming.
- [ ] Have a valid `GEMINI_API_KEY` in `.env`.
- [ ] Open `docs/architecture.svg` in a browser tab.
- [ ] Open the Antigravity IDE with the project loaded.
- [ ] Open `skywatcher/tools/security.py` and `sky_math.py` for cutaways.
- [ ] Record at 1080p; use a clean terminal font.
- [ ] Keep it under 5:00 — aim for 4:45.
- [ ] Upload to YouTube; set as unlisted if you don't want it public yet.
