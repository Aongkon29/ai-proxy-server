"""Skywatcher multi-agent system.

This package contains the agent definitions built on Google's Agent
Development Kit (ADK). The architecture is a coordinator + 3 specialist
sub-agents:

    ┌──────────────────────────────────────────────────────────┐
    │                   Coordinator (root)                      │
    │  Routes the user's request to the right specialist.      │
    └───────────────┬──────────────┬───────────────┬───────────┘
                   │              │               │
          ┌────────▼───────┐ ┌────▼─────────┐ ┌───▼──────────┐
          │ Satellite Data │ │  Sky Math    │ │  Educator    │
          │ Agent          │ │  Agent       │ │  Agent       │
          │ (CelesTrak     │ │ (pass        │ │ (general     │
          │  lookups)      │ │  prediction) │ │  space Q&A)  │
          └────────────────┘ └──────────────┘ └──────────────┘
                 │                  │
            function tools     MCP tools
            (direct import)    (consumes our
                              MCP server)

This demonstrates the 'Agent / Multi-agent system (ADK)' course concept.
"""
