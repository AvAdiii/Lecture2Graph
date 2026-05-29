"""Groq-backed LLM engine."""

from __future__ import annotations

import json
import re
import time
from pathlib import Path

from lecture2graph.utils.io import write_json
from lecture2graph.utils.env import get_env
from lecture2graph.utils.text import compact_snippet, humanize_concept, slugify, titleize_concept


CONCEPT_PROMPT = """You are an expert computer science educator analyzing a lecture transcript.
Extract the distinct computer science or technical concepts taught in the lecture.

Rules:
- Only return concepts relevant to computer science, programming, databases, algorithms, or math foundations.
- Normalize concepts to human-readable names, not sentences.
- Merge duplicates and synonyms.
- For each concept, provide mention_count, first_mention, sources, and up to 5 mention_details.

Return JSON with this shape only:
{
  "concepts": [
    {
      "name": "binary tree",
      "description": "A tree where each node has at most two children.",
      "mention_count": 4,
      "first_mention": 12.5,
      "sources": ["asr", "ocr"],
      "mention_details": [
        {"start": 12.5, "end": 18.1, "source": "asr", "text": "binary tree has left and right child"}
      ]
    }
  ]
}"""


GRAPH_PROMPT = """You are an expert computer science educator building a prerequisite graph.
Given concepts from a lecture, determine the knowledge dependencies between them.

Rules:
- Only add edges when understanding the source genuinely helps before the target.
- The graph must be a DAG.
- Use evidence values from: domain_rule, causal, llm.
- Use relation values from: prerequisite, refines, part_of.
- Include a short reason.
- Return a complete topological order covering every concept.

Return JSON with this shape only:
{
  "edges": [
    {
      "source": "tree",
      "target": "binary tree",
      "evidence": "domain_rule",
      "relation": "prerequisite",
      "confidence": 0.9,
      "reason": "Binary trees are a specialized kind of tree."
    }
  ],
  "topological_order": ["tree", "binary tree"]
}"""


class GroqEngine:
    name = "groq"
    label = "Groq"
    requires_api_key = True
    model = "llama-3.3-70b-versatile"

    def _client(self, api_key: str):
        from groq import Groq

        return Groq(api_key=api_key)

    def _resolve_api_key(self, api_key: str | None) -> str:
        resolved = api_key or get_env("GROQ_API_KEY")
        if not resolved:
            raise ValueError("The groq engine requires GROQ_API_KEY or --api-key.")
        return resolved

    def _complete_json(self, *, api_key: str, system_prompt: str, user_prompt: str) -> dict:
        client = self._client(api_key)
        delay = 10
        for attempt in range(4):
            try:
                response = client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.1,
                    max_tokens=8000,
                    response_format={"type": "json_object"},
                )
                content = response.choices[0].message.content.strip()
                content = re.sub(r"^```(?:json)?\s*", "", content)
                content = re.sub(r"\s*```$", "", content)
                return json.loads(content)
            except Exception as exc:
                message = str(exc).lower()
                if "rate_limit" in message or "429" in message:
                    time.sleep(delay)
                    delay *= 2
                    continue
                raise
        raise RuntimeError("Groq request failed after multiple retries.")

    def extract_concepts(self, *, video_id: str, data_dir: Path, normalized_segments: list[dict], registry, api_key: str | None = None) -> dict:
        api_key = self._resolve_api_key(api_key)
        transcript_lines = [
            f"[{segment['start']:.0f}s|{segment.get('source', '?')[0]}] {compact_snippet(segment['text'], 150)}"
            for segment in normalized_segments
        ]
        result = self._complete_json(
            api_key=api_key,
            system_prompt=CONCEPT_PROMPT,
            user_prompt="\n".join(transcript_lines),
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
        concepts = concepts_payload.get("concepts", [])
        concept_lines = [
            f"- {concept['name']} (mentions={concept['mention_count']}, first={concept['first_mention']:.1f}s)"
            for concept in concepts
        ]
        transcript = [
            f"[{segment['start']:.0f}s|{segment.get('source', '?')[0]}] {compact_snippet(segment['text'], 140)}"
            for segment in normalized_segments[:120]
        ]
        result = self._complete_json(
            api_key=api_key,
            system_prompt=GRAPH_PROMPT,
            user_prompt="CONCEPTS:\n" + "\n".join(concept_lines) + "\n\nTRANSCRIPT:\n" + "\n".join(transcript),
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
                for concept in concepts
            ],
            "edges": result.get("edges", []),
            "topological_order": result.get("topological_order", [concept["name"] for concept in concepts]),
            "causal_anchors_detected": 0,
        }
        write_json(data_dir / "graph.json", payload)
        return payload
