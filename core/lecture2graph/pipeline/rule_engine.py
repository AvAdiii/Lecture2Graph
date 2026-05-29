"""Default rule-based concept and DAG engine."""

from __future__ import annotations

import re
from collections import defaultdict, deque
from pathlib import Path

from lecture2graph.plugins.base import DomainPlugin, PrerequisiteRule
from lecture2graph.utils.io import write_json
from lecture2graph.utils.text import compact_snippet, humanize_concept, slugify, titleize_concept


CAUSAL_PATTERNS = [
    (
        r"before\s+(?:we\s+)?(?:do|discuss|learn|see|talk)\s+(.+?),\s*(?:you\s+)?(?:need|must|should)\s+(?:to\s+)?(?:know|understand|learn)\s+(.+)",
        "prerequisite_explicit",
    ),
    (r"first\s+(?:we\s+)?(?:write|do|see|learn)\s+(.+?),\s*then\s+(.+)", "temporal_sequence"),
    (r"(?:remember|recall|as\s+we\s+(?:saw|discussed|did))\s+(.+?)(?:\s+from\s+before|\s+earlier|\?)", "back_reference"),
    (r"(\w[\w\s-]+)\s+means\s+(\w[\w\s-]+)", "definition"),
]

OCR_DEDUP_WINDOW = 10.0
MAX_TEMPORAL_OUT = 3
TEMPORAL_GAP_MIN = 30


def _domain_patterns(domains: list[DomainPlugin]) -> dict[str, list[str]]:
    patterns: dict[str, list[str]] = {}
    for domain in domains:
        for concept, concept_patterns in domain.concept_patterns.items():
            patterns.setdefault(concept, []).extend(concept_patterns)
    return patterns


def _ocr_keywords(domains: list[DomainPlugin]) -> dict[str, str]:
    keywords: dict[str, str] = {}
    for domain in domains:
        keywords.update(domain.ocr_keywords)
    return keywords


def _fragment_aliases(domains: list[DomainPlugin]) -> dict[str, str]:
    aliases: dict[str, str] = {}
    for domain in domains:
        aliases.update(domain.fragment_aliases)
    return aliases


def _rules(domains: list[DomainPlugin]) -> list[PrerequisiteRule]:
    rules: list[PrerequisiteRule] = []
    for domain in domains:
        rules.extend(domain.prerequisite_rules)
    return rules


def _segment_ocr_keywords(segment: dict) -> list[str]:
    if "ocr_keywords" in segment:
        return [keyword for keyword in segment.get("ocr_keywords", []) if len(keyword.strip()) >= 2]
    if segment.get("source") != "ocr":
        return []
    return [chunk.strip() for chunk in re.split(r"[\s,;|]+", segment.get("text", "")) if len(chunk.strip()) >= 2]


def _segment_text(segment: dict) -> str:
    return segment.get("text", segment.get("spoken_text", ""))


def _extract_concepts_from_text(text: str, patterns: dict[str, list[str]]) -> set[str]:
    lowered = text.lower()
    found = set()
    for concept, concept_patterns in patterns.items():
        if any(re.search(pattern, lowered) for pattern in concept_patterns):
            found.add(concept)
    return found


def _extract_concepts_from_ocr(words: list[str], ocr_keywords: dict[str, str]) -> set[str]:
    found = set()
    for word in words:
        lowered = word.lower().strip()
        if lowered in ocr_keywords:
            found.add(ocr_keywords[lowered])
        for key, concept in ocr_keywords.items():
            if " " in key and key in lowered:
                found.add(concept)
    return found


def _find_concepts_in_text(text: str, aliases: dict[str, str], present_concepts: set[str]) -> set[str]:
    lowered = text.lower().strip()
    found = set()
    for fragment, concept in sorted(aliases.items(), key=lambda item: -len(item[0])):
        if concept in present_concepts and fragment in lowered:
            found.add(concept)
    return found


def _causal_edges(segments: list[dict], present_concepts: set[str], aliases: dict[str, str]) -> tuple[list[dict], int]:
    edges: list[dict] = []
    seen: set[tuple[str, str]] = set()
    anchor_count = 0

    for segment in segments:
        text = _segment_text(segment).lower()
        for pattern, anchor_type in CAUSAL_PATTERNS:
            for match in re.finditer(pattern, text):
                anchor_count += 1
                groups = [group for group in match.groups() if group]
                if len(groups) < 2:
                    continue
                if anchor_type == "definition":
                    targets = _find_concepts_in_text(groups[0], aliases, present_concepts)
                    prereqs = _find_concepts_in_text(groups[1], aliases, present_concepts)
                else:
                    prereqs = _find_concepts_in_text(groups[1], aliases, present_concepts)
                    targets = _find_concepts_in_text(groups[0], aliases, present_concepts)

                for prereq in prereqs:
                    for target in targets:
                        pair = (prereq, target)
                        if prereq == target or pair in seen:
                            continue
                        seen.add(pair)
                        edges.append(
                            {
                                "source": prereq,
                                "target": target,
                                "evidence": "causal",
                                "relation": "prerequisite",
                                "confidence": 0.74 if anchor_type == "definition" else 0.7,
                                "reason": compact_snippet(_segment_text(segment), max_length=120),
                            }
                        )
    return edges, anchor_count


def _compute_reachable(adjacency: dict[str, list[str]], start: str) -> set[str]:
    visited = set()
    queue = deque([start])
    while queue:
        node = queue.popleft()
        if node in visited:
            continue
        visited.add(node)
        for neighbor in adjacency.get(node, []):
            queue.append(neighbor)
    visited.discard(start)
    return visited


def _build_temporal_edges(concepts: list[dict], strong_edges: list[dict]) -> list[dict]:
    adjacency: dict[str, list[str]] = defaultdict(list)
    for edge in strong_edges:
        adjacency[edge["source"]].append(edge["target"])

    reachable = {concept["name"]: _compute_reachable(adjacency, concept["name"]) for concept in concepts}
    edges: list[dict] = []
    outgoing_count: dict[str, int] = defaultdict(int)

    for index, concept in enumerate(concepts):
        for later in concepts[index + 1 :]:
            if later["name"] in reachable.get(concept["name"], set()):
                continue
            if concept["name"] in reachable.get(later["name"], set()):
                continue
            gap = later["first_mention"] - concept["first_mention"]
            if gap <= TEMPORAL_GAP_MIN or outgoing_count[concept["name"]] >= MAX_TEMPORAL_OUT:
                continue
            confidence = max(0.3, min(0.5, 1.0 - gap / 400))
            edges.append(
                {
                    "source": concept["name"],
                    "target": later["name"],
                    "evidence": "temporal",
                    "relation": "prerequisite",
                    "confidence": round(confidence, 2),
                    "reason": f"Appears about {int(gap)} seconds earlier in the lecture.",
                }
            )
            outgoing_count[concept["name"]] += 1

    return edges


def _is_dag(nodes: list[str], edges: list[dict]) -> bool:
    adjacency: dict[str, list[str]] = defaultdict(list)
    in_degree = {node: 0 for node in nodes}
    for edge in edges:
        adjacency[edge["source"]].append(edge["target"])
        in_degree[edge["target"]] += 1

    queue = deque(sorted(node for node, degree in in_degree.items() if degree == 0))
    visited = 0
    while queue:
        node = queue.popleft()
        visited += 1
        for neighbor in adjacency.get(node, []):
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)
    return visited == len(nodes)


def _verify_dag(nodes: list[str], edges: list[dict]) -> list[dict]:
    checked = list(edges)
    while checked and not _is_dag(nodes, checked):
        checked = sorted(checked, key=lambda item: item["confidence"], reverse=True)
        checked.pop()
    return checked


def _topological_order(nodes: list[str], edges: list[dict]) -> list[str]:
    adjacency: dict[str, list[str]] = defaultdict(list)
    in_degree = {node: 0 for node in nodes}
    for edge in edges:
        adjacency[edge["source"]].append(edge["target"])
        in_degree[edge["target"]] += 1

    queue = deque(sorted(node for node, degree in in_degree.items() if degree == 0))
    order: list[str] = []
    while queue:
        node = queue.popleft()
        order.append(node)
        for neighbor in sorted(adjacency.get(node, [])):
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)
    return order


class RulesEngine:
    name = "rules"
    label = "Rules"
    requires_api_key = False

    def extract_concepts(
        self,
        *,
        video_id: str,
        data_dir: Path,
        normalized_segments: list[dict],
        registry,
        api_key: str | None = None,
    ) -> dict:
        domains = registry.domains()
        patterns = _domain_patterns(domains)
        ocr_keywords = _ocr_keywords(domains)
        descriptions = registry.domain_descriptions()

        concept_mentions: dict[str, list[dict]] = defaultdict(list)
        last_ocr_only: dict[str, float] = {}

        for segment in normalized_segments:
            text = _segment_text(segment)
            start = segment["start"]
            spoken_concepts = _extract_concepts_from_text(text, patterns)
            for concept in spoken_concepts:
                concept_mentions[concept].append(
                    {
                        "start": segment["start"],
                        "end": segment["end"],
                        "source": segment.get("source", "asr"),
                        "text": compact_snippet(text),
                    }
                )

            ocr_concepts = _extract_concepts_from_ocr(_segment_ocr_keywords(segment), ocr_keywords)
            for concept in ocr_concepts:
                if concept in spoken_concepts and concept_mentions[concept]:
                    concept_mentions[concept][-1]["source"] = "asr+ocr"
                    continue
                last_seen = last_ocr_only.get(concept, -999.0)
                if start - last_seen <= OCR_DEDUP_WINDOW:
                    continue
                concept_mentions[concept].append(
                    {
                        "start": segment["start"],
                        "end": segment["end"],
                        "source": "ocr",
                        "text": compact_snippet(text),
                    }
                )
                last_ocr_only[concept] = start

        concepts = []
        for concept_name, mentions in sorted(concept_mentions.items(), key=lambda item: min(m["start"] for m in item[1])):
            first = min(item["start"] for item in mentions)
            last = max(item["end"] for item in mentions)
            concepts.append(
                {
                    "id": slugify(concept_name),
                    "name": concept_name,
                    "label": titleize_concept(concept_name),
                    "slug": slugify(concept_name),
                    "description": descriptions.get(concept_name, f"Discussed in the lecture in the context of {humanize_concept(concept_name)}."),
                    "mention_count": len(mentions),
                    "first_mention": round(first, 1),
                    "last_mention": round(last, 1),
                    "sources": sorted(set(item["source"] for item in mentions)),
                    "mention_details": mentions,
                }
            )

        payload = {"video_id": video_id, "engine": self.name, "concepts": concepts}
        write_json(data_dir / "concepts.json", payload)
        return payload

    def build_graph(
        self,
        *,
        video_id: str,
        data_dir: Path,
        normalized_segments: list[dict],
        concepts_payload: dict,
        registry,
        api_key: str | None = None,
    ) -> dict:
        domains = registry.domains()
        concept_names = [concept["name"] for concept in concepts_payload.get("concepts", [])]
        present = set(concept_names)

        domain_edges = []
        for rule in _rules(domains):
            if rule.source in present and rule.target in present:
                domain_edges.append(
                    {
                        "source": rule.source,
                        "target": rule.target,
                        "evidence": "domain_rule",
                        "relation": rule.relation,
                        "confidence": rule.confidence,
                        "reason": rule.reason,
                    }
                )

        causal_edges, anchor_count = _causal_edges(normalized_segments, present, _fragment_aliases(domains))
        strong_edges = domain_edges + causal_edges
        temporal_edges = _build_temporal_edges(concepts_payload["concepts"], strong_edges)

        merged: list[dict] = []
        seen_pairs: set[tuple[str, str]] = set()
        for edge in domain_edges + causal_edges + temporal_edges:
            pair = (edge["source"], edge["target"])
            if pair in seen_pairs or edge["source"] == edge["target"]:
                continue
            seen_pairs.add(pair)
            merged.append(edge)

        clean_edges = _verify_dag(concept_names, merged)
        topological_order = _topological_order(concept_names, clean_edges)

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
                for concept in concepts_payload["concepts"]
            ],
            "edges": clean_edges,
            "topological_order": topological_order,
            "causal_anchors_detected": anchor_count,
        }
        write_json(data_dir / "graph.json", payload)
        return payload
