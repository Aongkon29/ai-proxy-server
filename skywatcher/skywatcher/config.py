"""Centralized configuration for Skywatcher.

All secrets are read from environment variables ONLY — never hardcoded.
This is part of the project's security posture: no API keys in source.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

# Load .env from multiple locations to handle different working directories.
# 1. Try the project root (skywatcher/.env — two levels up from this file)
# 2. Fall back to the current working directory (standard load_dotenv behavior)
_project_env = Path(__file__).resolve().parent.parent / ".env"
if _project_env.exists():
    load_dotenv(_project_env, override=True)
else:
    load_dotenv()


@dataclass(frozen=True)
class Settings:
    """Immutable runtime settings. Frozen so agents can't mutate config at runtime."""

    gemini_api_key: str = field(default_factory=lambda: os.getenv("GEMINI_API_KEY", ""))
    gemini_model: str = field(default_factory=lambda: os.getenv("GEMINI_MODEL", "gemini-2.5-flash"))

    # DeepSeek (OpenAI-compatible) — used when Gemini is geo-blocked/unavailable.
    deepseek_api_key: str = field(default_factory=lambda: os.getenv("DEEPSEEK_API_KEY", ""))
    deepseek_model: str = field(default_factory=lambda: os.getenv("DEEPSEEK_MODEL", "deepseek-chat"))

    # Default observer location (Boulder, CO — a public, well-known astronomy spot).
    # Users override per-query; we never store personal addresses.
    default_lat: float = field(default_factory=lambda: float(os.getenv("DEFAULT_LAT", "40.014984")))
    default_lon: float = field(default_factory=lambda: float(os.getenv("DEFAULT_LON", "-105.270546")))

    celestrak_timeout: int = field(default_factory=lambda: int(os.getenv("CELESTRAK_TIMEOUT", "15")))

    # Local cache for TLE data so we're polite to the free CelesTrak service.
    cache_dir: Path = field(default_factory=lambda: Path(".cache"))

    @property
    def has_gemini_key(self) -> bool:
        """True if a real Gemini key is configured."""
        return bool(self.gemini_api_key and self.gemini_api_key != "your_gemini_api_key_here")

    @property
    def has_deepseek_key(self) -> bool:
        """True if a DeepSeek API key is configured."""
        return bool(self.deepseek_api_key and self.deepseek_api_key != "your_deepseek_api_key_here")

    @property
    def has_api_key(self) -> bool:
        """True if any LLM provider key is configured."""
        return self.has_gemini_key or self.has_deepseek_key

    @property
    def llm_model(self):
        """Return the model object to pass to ADK's Agent(model=...).

        - DeepSeek (via LiteLlm) takes priority, since it works globally and
          Gemini is geo-blocked in some regions.
        - Falls back to a Gemini model string (native ADK) if only a Gemini
          key is set.
        """
        if self.has_deepseek_key:
            from google.adk.models.lite_llm import LiteLlm

            return LiteLlm(model=f"deepseek/{self.deepseek_model}")
        # Native Gemini: ADK accepts the model name string directly.
        return self.gemini_model

    def ensure_cache(self) -> Path:
        """Create and return the cache directory."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        return self.cache_dir


settings = Settings()
