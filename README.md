# AI Proxy Server

A lightweight AI API proxy and multi-agent satellite tracking project.

## Overview

This repository contains two main components:

- **`api/`** — A serverless edge function that proxies chat completion requests to the DeepSeek API, deployed on Vercel.
- **`skywatcher/`** — A multi-agent AI companion (capstone project) that tracks satellites, predicts visible passes, and answers space questions — built with Google ADK, MCP, and Skyfield.

## Projects

### 1. AI Proxy (`api/`)

A minimal Vercel Edge Function that forwards chat requests to DeepSeek's API. Keeps your API key server-side and provides a clean proxy endpoint.

**Stack:** Vercel Edge Functions · DeepSeek API

**Endpoint:** `POST /api/chat`

**Request body:**
```json
{
  "prompt": "Your message here"
}
```

**Setup:**
1. Set `DEEPSEEK_API_KEY` as an environment variable in Vercel
2. Deploy with `vercel --prod`

### 2. Skywatcher (`skywatcher/`)

A multi-agent AI system that turns plain-English questions into real orbital calculations. Ask "When can I see the ISS from Boulder?" and get accurate pass predictions.

**Stack:** Google ADK · MCP · Gemini/DeepSeek · Skyfield · CelesTrak

**Features:**
- 🛰️ Track recently launched satellites
- 🔭 Predict visible passes from any location
- 🤖 Multi-agent architecture (coordinator + 3 specialists)
- 🔌 MCP server for integration with Claude Desktop, Antigravity, Cursor, etc.
- 🐳 Docker-ready for easy deployment

See the [Skywatcher README](skywatcher/README.md) for full documentation.

## Repository Structure

```
.
├── api/                    # AI proxy edge function
│   ├── chat.js             # DeepSeek chat proxy handler
│   └── vercel.json         # Vercel config
└── skywatcher/             # Multi-agent satellite tracker
    ├── skywatcher/         # Core package (agents, tools, mcp_server)
    ├── tests/              # Unit tests
    ├── docs/               # Architecture diagrams & scripts
    └── README.md           # Full Skywatcher documentation
```

## License

MIT — see [LICENSE](skywatcher/LICENSE).
