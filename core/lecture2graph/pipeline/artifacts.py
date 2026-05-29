"""Result shaping and export helpers."""

from __future__ import annotations

from pathlib import Path

from lecture2graph.config import DEFAULT_EXPORT_BUNDLE
from lecture2graph.models import (
    ArtifactBundle,
    ConceptNode,
    ConceptRef,
    GraphBundle,
    GraphEdge,
    GraphNode,
    LectureGraphResult,
    LearningPathStep,
    RunStats,
    TimestampLink,
    TranscriptBundle,
    TranscriptSegment,
    VideoMetadata,
)
from lecture2graph.pipeline.visualize import render_html
from lecture2graph.utils.io import read_json, write_json, write_text
from lecture2graph.utils.text import compact_snippet, slugify, titleize_concept
from lecture2graph.utils.time import format_seconds
from lecture2graph.utils.youtube import watch_url


LANGUAGE_LABELS = {
    "en": "English",
    "hi": "Hindi",
    "te": "Telugu",
    "ta": "Tamil",
    "kn": "Kannada",
    "ml": "Malayalam",
}


def _transcript_segments(items: list[dict]) -> list[TranscriptSegment]:
    return [TranscriptSegment(**segment) for segment in items]


def _fallback_description(concept: dict) -> str:
    details = concept.get("mention_details", [])
    if details:
        return compact_snippet(details[0].get("text", ""))
    return f"Discussed in the lecture as part of {concept['name']}."


def build_result(*, data_dir: Path, video_id: str, url: str, engine: str) -> LectureGraphResult:
    concepts_payload = read_json(data_dir / "concepts.json", default={"concepts": []})
    graph_payload = read_json(data_dir / "graph.json", default={"nodes": [], "edges": [], "topological_order": []})
    translated = read_json(data_dir / "transcript.json", default=[])
    original = read_json(data_dir / "transcript_original.json", default=translated)
    detected_language = read_json(data_dir / "detected_language.json", default={"language": "en"}).get("language", "en")

    concept_lookup = {
        concept["name"]: {
            **concept,
            "id": concept.get("id") or slugify(concept["name"]),
            "description": concept.get("description") or _fallback_description(concept),
        }
        for concept in concepts_payload.get("concepts", [])
    }
    id_by_name = {name: concept["id"] for name, concept in concept_lookup.items()}

    prerequisites_by_target: dict[str, list[ConceptRef]] = {}
    dependents_by_source: dict[str, list[ConceptRef]] = {}
    graph_edges = []
    for edge in graph_payload.get("edges", []):
        source_name = edge["source"]
        target_name = edge["target"]
        source_id = id_by_name.get(source_name)
        target_id = id_by_name.get(target_name)
        if not source_id or not target_id:
            continue

        graph_edges.append(
            GraphEdge(
                source=source_id,
                target=target_id,
                evidence=edge.get("evidence", "domain_rule"),
                relation=edge.get("relation", "prerequisite"),
                confidence=float(edge.get("confidence", 0.5)),
                reason=edge.get("reason", ""),
            )
        )
        prerequisites_by_target.setdefault(target_id, []).append(ConceptRef(id=source_id, name=titleize_concept(source_name)))
        dependents_by_source.setdefault(source_id, []).append(ConceptRef(id=target_id, name=titleize_concept(target_name)))

    concepts = []
    for concept_name, concept in concept_lookup.items():
        timestamp_links = [
            TimestampLink(
                seconds=float(detail.get("start", 0.0)),
                label=format_seconds(float(detail.get("start", 0.0))),
                url=watch_url(video_id, float(detail.get("start", 0.0))),
                source=detail.get("source", "unknown"),
            )
            for detail in concept.get("mention_details", [])[:12]
        ]
        concepts.append(
            ConceptNode(
                id=concept["id"],
                name=titleize_concept(concept_name),
                slug=concept["id"],
                description=concept["description"],
                mention_count=int(concept.get("mention_count", 0)),
                first_seen=float(concept.get("first_mention", 0.0)),
                last_seen=float(concept.get("last_mention", 0.0)),
                sources=concept.get("sources", []),
                timestamps=timestamp_links,
                prerequisites=prerequisites_by_target.get(concept["id"], []),
                dependents=dependents_by_source.get(concept["id"], []),
            )
        )

    concepts.sort(key=lambda item: item.first_seen)
    concept_by_id = {concept.id: concept for concept in concepts}
    topological_ids = [id_by_name[name] for name in graph_payload.get("topological_order", []) if name in id_by_name]

    graph_nodes = []
    levels = {node_id: index for index, node_id in enumerate(topological_ids)}
    for concept in concepts:
        graph_nodes.append(
            GraphNode(
                id=concept.id,
                label=concept.name,
                mention_count=concept.mention_count,
                level=levels.get(concept.id, 0),
                first_seen=concept.first_seen,
                description=concept.description,
            )
        )

    learning_path = []
    for step_number, concept_id in enumerate(topological_ids, start=1):
        concept = concept_by_id[concept_id]
        learning_path.append(
            LearningPathStep(
                step=step_number,
                concept_id=concept.id,
                title=concept.name,
                description=concept.description,
                prerequisite_ids=[item.id for item in concept.prerequisites],
                timestamp_url=concept.timestamps[0].url if concept.timestamps else None,
            )
        )

    graph = GraphBundle(nodes=graph_nodes, edges=graph_edges, topological_order=topological_ids)
    transcripts = TranscriptBundle(
        original=_transcript_segments(original),
        translated=_transcript_segments(translated),
    )

    bundle_path = data_dir / DEFAULT_EXPORT_BUNDLE
    notes_path = data_dir / "notes.md"
    graph_html_path = data_dir / "graph.html"

    result = LectureGraphResult(
        video=VideoMetadata(
            video_id=video_id,
            watch_url=url,
            source_language=detected_language,
            source_language_label=LANGUAGE_LABELS.get(detected_language, detected_language.upper()),
            engine=engine,
        ),
        stats=RunStats(
            concept_count=len(concepts),
            edge_count=len(graph_edges),
            learning_path_length=len(learning_path),
            transcript_segment_count=len(transcripts.translated),
            topological_coverage=f"{len(topological_ids)}/{len(concepts)}",
        ),
        transcripts=transcripts,
        concepts=concepts,
        graph=graph,
        learning_path=learning_path,
        artifacts=ArtifactBundle(
            data_dir=str(data_dir),
            graph_html=str(graph_html_path),
            notes_md=str(notes_path),
            bundle_json=str(bundle_path),
            concepts_json=str(data_dir / "concepts.json"),
            graph_json=str(data_dir / "graph.json"),
        ),
    )
    return result


def render_notes(result: LectureGraphResult) -> str:
    lines = [
        f"# {result.video.video_id} | Lecture2Graph Notes",
        "",
        f"- Source language: {result.video.source_language_label}",
        f"- Engine: {result.video.engine}",
        f"- Concepts: {result.stats.concept_count}",
        f"- Dependencies: {result.stats.edge_count}",
        f"- Watch: {result.video.watch_url}",
        "",
        "## Learning Path",
        "",
    ]

    for step in result.learning_path:
        lines.append(f"{step.step}. [{step.title}]({step.timestamp_url or result.video.watch_url})")
        lines.append(f"   - {step.description}")

    lines.extend(["", "## Concepts", ""])
    for concept in result.concepts:
        lines.append(f"### {concept.name}")
        lines.append(f"- Mentions: {concept.mention_count}")
        lines.append(f"- First seen: {format_seconds(concept.first_seen)}")
        lines.append(f"- Description: {concept.description}")
        if concept.prerequisites:
            lines.append("- Prerequisites: " + ", ".join(item.name for item in concept.prerequisites))
        if concept.dependents:
            lines.append("- Unlocks: " + ", ".join(item.name for item in concept.dependents))
        if concept.timestamps:
            lines.append("- Timestamps: " + ", ".join(f"[{item.label}]({item.url})" for item in concept.timestamps[:6]))
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def save_artifacts(result: LectureGraphResult) -> LectureGraphResult:
    data_dir = Path(result.artifacts.data_dir)
    write_json(data_dir / DEFAULT_EXPORT_BUNDLE, result.model_dump(mode="json"))
    write_text(data_dir / "notes.md", render_notes(result))
    write_text(data_dir / "graph.html", render_html(result))
    return result

