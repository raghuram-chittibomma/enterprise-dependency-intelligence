"""Load the project-root `.env` into `os.environ` (python-dotenv).

Idempotent — safe to call from multiple config modules. Existing process
environment variables always win over `.env` values.
"""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_LOADED = False


def load_project_env() -> None:
    global _LOADED
    if _LOADED:
        return
    load_dotenv(_PROJECT_ROOT / ".env", override=False)
    _LOADED = True
