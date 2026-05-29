"""Plugin interfaces and data structures."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class PrerequisiteRule:
    source: str
    target: str
    relation: str = "prerequisite"
    confidence: float = 0.8
    reason: str = ""


@dataclass(frozen=True)
class DomainPlugin:
    name: str
    concept_patterns: dict[str, list[str]] = field(default_factory=dict)
    ocr_keywords: dict[str, str] = field(default_factory=dict)
    prerequisite_rules: list[PrerequisiteRule] = field(default_factory=list)
    fragment_aliases: dict[str, str] = field(default_factory=dict)
    descriptions: dict[str, str] = field(default_factory=dict)


class EnginePlugin(Protocol):
    name: str
    label: str
    requires_api_key: bool

    def extract_concepts(
        self,
        *,
        video_id: str,
        data_dir: Path,
        normalized_segments: list[dict],
        registry: "PluginRegistry",
        api_key: str | None = None,
    ) -> dict:
        ...

    def build_graph(
        self,
        *,
        video_id: str,
        data_dir: Path,
        normalized_segments: list[dict],
        concepts_payload: dict,
        registry: "PluginRegistry",
        api_key: str | None = None,
    ) -> dict:
        ...

