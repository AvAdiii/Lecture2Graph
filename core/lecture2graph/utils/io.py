"""Small filesystem helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def ensure_dir(path: str | Path) -> Path:
    target = Path(path)
    target.mkdir(parents=True, exist_ok=True)
    return target


def read_json(path: str | Path, default: Any | None = None) -> Any:
    file_path = Path(path)
    if not file_path.exists():
        return default
    with file_path.open(encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: str | Path, payload: Any) -> Path:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with file_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
    return file_path


def write_text(path: str | Path, content: str) -> Path:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding="utf-8")
    return file_path

