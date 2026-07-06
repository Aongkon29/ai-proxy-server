# Skywatcher — Submission Checklist

Your deadline is **July 7, 2026, 2:59 PM GMT+8**. The code is done; here's what
*you* need to do to submit. Check off each item.

## 1. Get the code onto GitHub (required — public link)

```bash
cd /workspace/skywatcher
# Sanity check one more time:
pytest -q                      # should be 14 passed
skywatcher --help              # should print commands

# Then push to a NEW public GitHub repo:
git init
git add .
git commit -m "Skywatcher: multi-agent satellite tracker (Kaggle capstone)"
# Create an empty repo on github.com first, then:
git remote add origin https://github.com/<your-username>/skywatcher.git
git branch -M main
git push -u origin main
```

**Verify:** open the repo URL in an incognito window — it must be public and
the README must render.

## 2. Get a free Gemini API key & test the agent (so the demo works)

1. Go to <https://aistudio.google.com/apikey> → "Create API key" (free).
2. Put it in `/workspace/skywatcher/.env`:
   ```
   GEMINI_API_KEY=AIza...your_real_key
   ```
3. Test end-to-end:
   ```bash
   skywatcher ask "When can I see the ISS from New York?"
   skywatcher list-sats -c last-30-days
   ```
   If you see real pass predictions and a satellite list, you're good.
   *(Needs internet — the sandbox where I built this had none, but your
   machine will.)*

## 3. Record the 5-minute video

- Use `docs/VIDEO_SCRIPT.md` as your script (it's timed to ~4:45).
- Screen-record the terminal demos + the architecture SVG + Antigravity IDE.
- Upload to **YouTube** (unlisted is fine — judges can still view it).
- Copy the YouTube URL.

## 4. Make a cover image (required for the Kaggle Media Gallery)

Easiest option: open `docs/architecture.svg` in a browser, screenshot it, and
use that as the cover. Or screenshot a successful `skywatcher ask` response
with the architecture diagram beside it.

## 5. Create the Kaggle Writeup

1. On Kaggle, click **"New Writeup"** (on the capstone page).
2. **Title:** `Skywatcher: A Multi-Agent Companion for What's Overhead`
3. **Subtitle:** `Turning "what's in the sky tonight?" into real orbital math — with ADK, MCP, Gemini, and Skyfield.`
4. **Track:** Freestyle
5. Paste the contents of `/workspace/skywatcher/WRITEUP.md` into the writeup
   body (it's ~1,233 words, well under the 2,500 limit).
6. **Media Gallery:** upload your cover image + attach the YouTube video.
7. **Public Project Link:** paste your GitHub repo URL.

## 6. Submit

Click **"Submit"** in the top-right of the Writeup (NOT just "Save" — drafts
aren't judged). Do this **before** 2:59 PM GMT+8 on July 7.

---

## Quick verification before you submit

- [ ] GitHub repo is **public** (check in incognito).
- [ ] README renders and has setup instructions.
- [ ] `pytest -q` passes with 14 tests.
- [ ] `skywatcher ask "..."` returns a real answer with a valid API key.
- [ ] Video is on YouTube and ≤ 5 minutes.
- [ ] Writeup is saved + track = Freestyle.
- [ ] Cover image attached to Media Gallery.
- [ ] Video attached to Media Gallery.
- [ ] GitHub link attached as Public Project Link.
- [ ] **"Submit" button clicked** (not just Save).

---

## File map (what's where)

| File | What it is |
|------|------------|
| `README.md` | Project documentation (20 pts) |
| `WRITEUP.md` | Kaggle writeup text to paste (10 pts) |
| `docs/VIDEO_SCRIPT.md` | Your 5-min video script (10 pts) |
| `docs/architecture.svg` | Architecture diagram — use as cover image |
| `Dockerfile`, `docker-compose.yml` | Deployability |
| `skywatcher/agents/` | Multi-agent system (ADK) |
| `skywatcher/mcp_server/server.py` | MCP server |
| `skywatcher/tools/security.py` | Security features |
| `skywatcher/cli.py` | Agents CLI |
| `tests/test_tools.py` | 14 unit tests |

## If something breaks

- **`skywatcher ask` says "needs a Gemini API key"** → your `.env` isn't loaded
  or the key is wrong. Re-check step 2.
- **`skywatcher list-sats` hangs** → no internet, or CelesTrak is slow. Retry;
  the cache makes subsequent calls instant.
- **`pytest` fails** → re-run `pip install -e ".[dev]"` and `pip install
  skyfield sgp4 httpx click rich python-dotenv pydantic`.
- **ADK import error** → `pip install google-adk google-genai`.
