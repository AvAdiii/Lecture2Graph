"""Registry for builtin and external plugins."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Iterable

from lecture2graph.config import split_plugin_paths

from .base import DomainPlugin, EnginePlugin


class PluginRegistry:
    def __init__(self) -> None:
        self._domains: dict[str, DomainPlugin] = {}
        self._engines: dict[str, EnginePlugin] = {}

    def register_domain(self, plugin: DomainPlugin) -> None:
        self._domains[plugin.name] = plugin

    def register_engine(self, plugin: EnginePlugin) -> None:
        self._engines[plugin.name] = plugin

    def domains(self) -> list[DomainPlugin]:
        return list(self._domains.values())

    def domain_descriptions(self) -> dict[str, str]:
        descriptions: dict[str, str] = {}
        for domain in self.domains():
            descriptions.update(domain.descriptions)
        return descriptions

    def get_engine(self, name: str) -> EnginePlugin:
        try:
            return self._engines[name]
        except KeyError as exc:
            raise KeyError(f"Unknown Lecture2Graph engine: {name}") from exc

    def engines(self) -> list[EnginePlugin]:
        return list(self._engines.values())

    def load_external_plugins(self, paths: Iterable[Path] | None = None) -> None:
        for path in paths or split_plugin_paths():
            self._load_plugin_path(path)

    def _load_plugin_path(self, path: Path) -> None:
        if not path.exists():
            return

        candidates = [path]
        if path.is_dir():
            candidates = sorted(path.glob("*.py"))

        for candidate in candidates:
            if candidate.name.startswith("_") or candidate.suffix != ".py":
                continue
            module_name = f"lecture2graph_external_{candidate.stem}"
            spec = importlib.util.spec_from_file_location(module_name, candidate)
            if spec is None or spec.loader is None:
                continue
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            register = getattr(module, "register", None)
            if callable(register):
                register(self)


_REGISTRY: PluginRegistry | None = None


def _bootstrap_registry() -> PluginRegistry:
    from lecture2graph.pipeline.gemini_engine import GeminiEngine
    from lecture2graph.pipeline.groq_engine import GroqEngine
    from lecture2graph.pipeline.openai_engine import OpenAIEngine
    from lecture2graph.pipeline.rule_engine import RulesEngine
    from lecture2graph.plugins.builtin_domains.core_cs import PLUGIN as CORE_CS_PLUGIN
    from lecture2graph.plugins.builtin_domains.databases import PLUGIN as DATABASE_PLUGIN
    from lecture2graph.plugins.builtin_domains.graphs import PLUGIN as GRAPHS_PLUGIN
    from lecture2graph.plugins.builtin_domains.sorting import PLUGIN as SORTING_PLUGIN
    from lecture2graph.plugins.builtin_domains.trees import PLUGIN as TREES_PLUGIN

    registry = PluginRegistry()
    for domain_plugin in (
        TREES_PLUGIN,
        GRAPHS_PLUGIN,
        DATABASE_PLUGIN,
        SORTING_PLUGIN,
        CORE_CS_PLUGIN,
    ):
        registry.register_domain(domain_plugin)

    registry.register_engine(RulesEngine())
    registry.register_engine(GroqEngine())
    registry.register_engine(GeminiEngine())
    registry.register_engine(OpenAIEngine())
    registry.load_external_plugins()
    return registry


def get_registry() -> PluginRegistry:
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = _bootstrap_registry()
    return _REGISTRY
