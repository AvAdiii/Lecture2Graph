"""Pydantic models shared by the CLI, Streamlit app, and exports."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


EdgeEvidence = Literal["domain_rule", "causal", "temporal", "llm"]
EdgeRelation = Literal["prerequisite", "refines", "part_of"]
SegmentSource = Literal["asr", "ocr", "asr+ocr", "unknown"]


class PipelineRequest(BaseModel):
    url: str
    engine: str = "rules"
    whisper_model: str = "small"
    data_root: str | None = None
    force_from: str | None = None
    api_key: str | None = None


class TranscriptSegment(BaseModel):
    start: float
    end: float
    text: str
    source: SegmentSource = "unknown"
    lang: str = "en"
    source_lang: str = "en"


class TranscriptBundle(BaseModel):
    original: list[TranscriptSegment] = Field(default_factory=list)
    translated: list[TranscriptSegment] = Field(default_factory=list)


class TimestampLink(BaseModel):
    seconds: float
    label: str
    url: str
    source: SegmentSource = "unknown"


class ConceptRef(BaseModel):
    id: str
    name: str


class ConceptNode(BaseModel):
    id: str
    name: str
    slug: str
    description: str
    mention_count: int
    first_seen: float
    last_seen: float
    sources: list[SegmentSource] = Field(default_factory=list)
    timestamps: list[TimestampLink] = Field(default_factory=list)
    prerequisites: list[ConceptRef] = Field(default_factory=list)
    dependents: list[ConceptRef] = Field(default_factory=list)


class GraphNode(BaseModel):
    id: str
    label: str
    mention_count: int
    level: int = 0
    first_seen: float = 0.0
    description: str = ""


class GraphEdge(BaseModel):
    source: str
    target: str
    evidence: EdgeEvidence
    relation: EdgeRelation = "prerequisite"
    confidence: float = 0.5
    reason: str = ""


class GraphBundle(BaseModel):
    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)
    topological_order: list[str] = Field(default_factory=list)


class LearningPathStep(BaseModel):
    step: int
    concept_id: str
    title: str
    description: str
    prerequisite_ids: list[str] = Field(default_factory=list)
    timestamp_url: str | None = None


class VideoMetadata(BaseModel):
    video_id: str
    watch_url: str
    source_language: str = "en"
    source_language_label: str = "English"
    engine: str = "rules"
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class ArtifactBundle(BaseModel):
    data_dir: str
    graph_html: str
    notes_md: str
    bundle_json: str
    concepts_json: str
    graph_json: str


class RunStats(BaseModel):
    concept_count: int
    edge_count: int
    learning_path_length: int
    transcript_segment_count: int
    topological_coverage: str


class LectureGraphResult(BaseModel):
    video: VideoMetadata
    stats: RunStats
    transcripts: TranscriptBundle
    concepts: list[ConceptNode]
    graph: GraphBundle
    learning_path: list[LearningPathStep]
    artifacts: ArtifactBundle


class SampleLecture(BaseModel):
    video_id: str
    title: str
    topic: str
    language: str
    watch_url: str
    preview_concepts: list[str] = Field(default_factory=list)
