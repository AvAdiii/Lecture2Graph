"""OpenAI-backed LLM engine."""

from __future__ import annotations

import json
from pathlib import Path

from lecture2graph.pipeline.groq_engine import CONCEPT_PROMPT, GRAPH_PROMPT
from lecture2graph.utils.env import get_env
from lecture2graph.utils.io import write_json
from lecture2graph.utils.text import compact_snippet, humanize_concept, slugify, titleize_concept


class OpenAIEngine:
    name = "openai"
    label = "OpenAI"
    requires_api_key = True
    model = "gpt-4.1-mini"

    def _client(self, api_key: str):
        from openai import OpenAI

        return OpenAI(api_key=api_key)

    def _resolve_api_key(self, api_key: str | None) -> str:
        resolved = api_key or get_env("OPENAI_API_KEY")
        if not resolved:
            raise ValueError("The openai engine requires OPENAI_API_KEY or --api-key.")
        return resolved

    def _generate_json(self, *, api_key: str, instructions: str, input_text: str) -> dict:
        client = self._client(api_key)
        response = client.responses.create(
            model=self.model,
            instructions=instructions,
            input=input_text,
            text={"format": {"type": "json_object"}},
        )
        return json.loads(response.output_text)

    def extract_concepts(self, *, video_id: str, data_dir: Path, normalized_segments: list[dict], registry, api_key: str | None = None) -> dict:
        api_key = self._resolve_api_key(api_key)
        transcript = "\n".join(
            f"[{segment['start']:.0f}s|{segment.get('source', '?')[0]}] {compact_snippet(segment['text'], 150)}"
            for segment in normalized_segments
        )
        result = self._generate_json(
            api_key=api_key,
            instructions=CONCEPT_PROMPT,
            input_text=transcript,
        )

        concepts = []
        for concept in result.get("concepts", []):
            name = humanize_concept(concept.get("name", "")).lower()
            concepts.append(
                {
                    "id": slugify(name),
                    "name": name,
                    "label": titleize_concept(name),
                    "slug": slugify(name),
                    "description": concept.get("description") or f"Discussed in the lecture in the context of {name}.",
                    "mention_count": int(concept.get("mention_count", 0) or concept.get("mentions", 0)),
                    "first_mention": float(concept.get("first_mention", concept.get("first_seen", 0.0))),
                    "last_mention": max(
                        [float(detail.get("end", detail.get("start", 0.0))) for detail in concept.get("mention_details", [])] or [float(concept.get("first_mention", concept.get("first_seen", 0.0)))]
                    ),
                    "sources": sorted(set(concept.get("sources", []))),
                    "mention_details": concept.get("mention_details", []),
                }
            )

        payload = {"video_id": video_id, "engine": self.name, "concepts": concepts}
        write_json(data_dir / "concepts.json", payload)
        return payload

    def build_graph(self, *, video_id: str, data_dir: Path, normalized_segments: list[dict], concepts_payload: dict, registry, api_key: str | None = None) -> dict:
        api_key = self._resolve_api_key(api_key)
        concept_lines = "\n".join(
            f"- {concept['name']} (mentions={concept['mention_count']}, first={concept['first_mention']:.1f}s)"
            for concept in concepts_payload.get("concepts", [])
        )
        transcript = "\n".join(
            f"[{segment['start']:.0f}s|{segment.get('source', '?')[0]}] {compact_snippet(segment['text'], 140)}"
            for segment in normalized_segments[:120]
        )
        result = self._generate_json(
            api_key=api_key,
            instructions=GRAPH_PROMPT,
            input_text="CONCEPTS:\n" + concept_lines + "\n\nTRANSCRIPT:\n" + transcript,
        )

        payload = {
            "video_id": video_id,
            "engine": self.name,
            "nodes": [
                {
                    "id": concept["name"],
                    "mention_count": concept["mention_count"],
                    "first_mention": concept["first_mention"],
                    "last_mention": concept["last_mention"],
                    "description": concept["description"],
                }
                for concept in concepts_payload.get("concepts", [])
            ],
            "edges": result.get("edges", []),
            "topological_order": result.get("topological_order", [concept["name"] for concept in concepts_payload.get("concepts", [])]),
            "causal_anchors_detected": 0,
        }
        write_json(data_dir / "graph.json", payload)
        return payload
