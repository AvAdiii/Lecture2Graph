"""Gemini-backed LLM engine."""

from __future__ import annotations

import json
from pathlib import Path

from lecture2graph.pipeline.groq_engine import CONCEPT_PROMPT, GRAPH_PROMPT
from lecture2graph.utils.env import get_env
from lecture2graph.utils.io import write_json
from lecture2graph.utils.text import compact_snippet, humanize_concept, slugify, titleize_concept


class GeminiEngine:
    name = "gemini"
    label = "Gemini"
    requires_api_key = True
    model = "gemini-2.5-flash"

    def _client(self, api_key: str):
        from google import genai

        return genai.Client(api_key=api_key)

    def _resolve_api_key(self, api_key: str | None) -> str:
        resolved = api_key or get_env("GEMINI_API_KEY")
        if not resolved:
            raise ValueError("The gemini engine requires GEMINI_API_KEY or --api-key.")
        return resolved

    def _generate_json(self, *, api_key: str, prompt: str, schema: dict) -> dict:
        client = self._client(api_key)
        response = client.models.generate_content(
            model=self.model,
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "response_json_schema": schema,
            },
        )
        return json.loads(response.text)

    def extract_concepts(self, *, video_id: str, data_dir: Path, normalized_segments: list[dict], registry, api_key: str | None = None) -> dict:
        api_key = self._resolve_api_key(api_key)
        transcript_lines = [
            f"[{segment['start']:.0f}s|{segment.get('source', '?')[0]}] {compact_snippet(segment['text'], 150)}"
            for segment in normalized_segments
        ]
        schema = {
            "type": "object",
            "properties": {
                "concepts": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "description": {"type": "string"},
                            "mention_count": {"type": "integer"},
                            "first_mention": {"type": "number"},
                            "sources": {"type": "array", "items": {"type": "string"}},
                            "mention_details": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "start": {"type": "number"},
                                        "end": {"type": "number"},
                                        "source": {"type": "string"},
                                        "text": {"type": "string"},
                                    },
                                    "required": ["start", "source", "text"],
                                    "additionalProperties": False,
                                },
                            },
                        },
                        "required": ["name", "mention_count", "first_mention", "sources", "mention_details"],
                        "additionalProperties": False,
                    },
                }
            },
            "required": ["concepts"],
            "additionalProperties": False,
        }
        result = self._generate_json(api_key=api_key, prompt=CONCEPT_PROMPT + "\n\n" + "\n".join(transcript_lines), schema=schema)

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
                    "mention_count": int(concept.get("mention_count", 0)),
                    "first_mention": float(concept.get("first_mention", 0.0)),
                    "last_mention": max(
                        [float(detail.get("end", detail.get("start", 0.0))) for detail in concept.get("mention_details", [])] or [float(concept.get("first_mention", 0.0))]
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
        concept_lines = [
            f"- {concept['name']} (mentions={concept['mention_count']}, first={concept['first_mention']:.1f}s)"
            for concept in concepts_payload.get("concepts", [])
        ]
        transcript_lines = [
            f"[{segment['start']:.0f}s|{segment.get('source', '?')[0]}] {compact_snippet(segment['text'], 140)}"
            for segment in normalized_segments[:120]
        ]
        schema = {
            "type": "object",
            "properties": {
                "edges": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "source": {"type": "string"},
                            "target": {"type": "string"},
                            "evidence": {"type": "string"},
                            "relation": {"type": "string"},
                            "confidence": {"type": "number"},
                            "reason": {"type": "string"},
                        },
                        "required": ["source", "target", "evidence", "relation", "confidence", "reason"],
                        "additionalProperties": False,
                    },
                },
                "topological_order": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            },
            "required": ["edges", "topological_order"],
            "additionalProperties": False,
        }
        result = self._generate_json(
            api_key=api_key,
            prompt=GRAPH_PROMPT + "\n\nCONCEPTS:\n" + "\n".join(concept_lines) + "\n\nTRANSCRIPT:\n" + "\n".join(transcript_lines),
            schema=schema,
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
