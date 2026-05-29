"""Shared paths and configuration defaults."""

from __future__ import annotations

import os
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parent
REPO_ROOT = PACKAGE_ROOT.parent.parent
DEFAULT_DATA_ROOT = REPO_ROOT / "data"
DEFAULT_EXPORT_BUNDLE = "lecture2graph.json"
DEFAULT_ENGINE = "rules"
PLUGIN_ENV_VAR = "LECTURE2GRAPH_PLUGIN_PATHS"


def resolve_data_root(data_root: str | Path | None = None) -> Path:
    if data_root is None:
        root = DEFAULT_DATA_ROOT
    else:
        root = Path(data_root)
        if not root.is_absolute():
            root = (REPO_ROOT / root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def split_plugin_paths(value: str | None = None) -> list[Path]:
    raw = value if value is not None else os.getenv(PLUGIN_ENV_VAR, "")
    if not raw.strip():
        return []
    return [Path(part).expanduser().resolve() for part in raw.split(os.pathsep) if part.strip()]
