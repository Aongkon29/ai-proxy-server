"""Centralized configuration for Skywatcher.

All secrets are read from environment variables ONLY — never hardcoded.
This is part of the project's security posture: no API keys in source.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

# Load .env if present (local dev). In production, env vars come from the platform.
load_dotenv()


@dataclass(frozen=True)
class Settings:
    """Immutable runtime settings. Frozen so agents can't mutate config at runtime."""

    gemini_api_key: str = field(default_factory=lambda: os.getenv("GEMINI_API_KEY", ""))
    gemini_model: str = field(default_factory=lambda: os.getenv("GEMINI_MODEL", "gemini-2.0-flash"))

    # Default observer location (Boulder, CO — a public, well-known astronomy spot).
    # Users override per-query; we never store personal addresses.
    default_lat: float = field(default_factory=lambda: float(os.getenv("DEFAULT_LAT", "40.014984")))
    default_lon: float = field(default_factory=lambda: float(os.getenv("DEFAULT_LON", "-105.270546")))

    celestrak_timeout: int = field(default_factory=lambda: int(os.getenv("CELESTRAK_TIMEOUT", "15")))

    # Local cache for TLE data so we're polite to the free CelesTrak service.
    cache_dir: Path = field(default_factory=lambda: Path(".cache"))

    @property
    def has_api_key(self) -> bool:
        """True if a Gemini key is configured."""
        return bool(self.gemini_api_key and self.gemini_api_key != "your_gemini_api_key_here")

    def ensure_cache(self) -> Path:
        """Create and return the cache directory."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        return self.cache_dir


settings = Settings()
