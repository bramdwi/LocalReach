"""
helpers.py — Shared utilities for execution scripts.

Provides:
  - Environment variable loading (.env)
  - Structured logging
  - Common error formatting
"""

import logging
import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TMP_DIR = PROJECT_ROOT / ".tmp"
TMP_DIR.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------

def load_env() -> None:
    """Load .env from project root. Installs python-dotenv on first use."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "python-dotenv", "-q"])
        from dotenv import load_dotenv

    env_path = PROJECT_ROOT / ".env"
    if env_path.exists():
        load_dotenv(env_path)
    else:
        logging.warning(".env file not found at %s — using system env vars only.", env_path)


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def get_logger(name: str) -> logging.Logger:
    """Return a consistently formatted logger."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "[%(asctime)s] %(levelname)-8s %(name)s — %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())
    return logger


# ---------------------------------------------------------------------------
# Error helpers
# ---------------------------------------------------------------------------

def format_error(exc: Exception) -> str:
    """Return a one-line summary suitable for directive learnings."""
    return f"[{type(exc).__name__}] {exc}"
