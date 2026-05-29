"""Environment variable helpers."""

from __future__ import annotations

import os
from pathlib import Path

from lecture2graph.config import REPO_ROOT


def load_dotenv(dotenv_path: Path | None = None) -> None:
    target = dotenv_path or (REPO_ROOT / ".env")
    if not target.exists():
        return

    for line in target.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def get_env(name: str) -> str | None:
    load_dotenv()
    value = os.getenv(name)
    return value.strip() if value else None

