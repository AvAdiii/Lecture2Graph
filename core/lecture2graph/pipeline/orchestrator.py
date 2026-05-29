"""High-level pipeline orchestration."""

from __future__ import annotations

from pathlib import Path

from lecture2graph.config import DEFAULT_ENGINE, resolve_data_root
from lecture2graph.models import LectureGraphResult, PipelineRequest
from lecture2graph.plugins import get_registry
from lecture2graph.pipeline.artifacts import build_result, save_artifacts
from lecture2graph.utils.io import read_json, write_json
from lecture2graph.utils.youtube import get_video_id, normalize_url


STAGES = ["ingest", "extract", "normalize", "concepts", "graph", "artifacts"]


def _clear_outputs(data_dir: Path, stage: str | None) -> None:
    if not stage:
        return
    clear_map = {
        "extract": ["transcript.json", "transcript_original.json", "detected_language.json", "ocr_raw.json", "aligned_segments.json"],
        "normalize": ["normalized_segments.json", "asr_vocabulary.json"],
        "concepts": ["concepts.json"],
        "graph": ["graph.json"],
        "artifacts": ["lecture2graph.json", "graph.html", "notes.md"],
    }
    stage_index = STAGES.index(stage)
    for candidate_stage in STAGES[stage_index:]:
        for filename in clear_map.get(candidate_stage, []):
            path = data_dir / filename
            if path.exists():
                path.unlink()


def run_pipeline(request: PipelineRequest) -> LectureGraphResult:
    from lecture2graph.pipeline import extract, ingest, normalize

    registry = get_registry()
    engine_name = request.engine or DEFAULT_ENGINE
    engine = registry.get_engine(engine_name)
    data_root = resolve_data_root(request.data_root)
    normalized_url = normalize_url(request.url)

    ingest_result = ingest.run(normalized_url, data_root)
    data_dir = Path(ingest_result["data_dir"])
    _clear_outputs(data_dir, request.force_from)

    extract_result = extract.run(ingest_result["audio_path"], ingest_result["frames_dir"], model_size=request.whisper_model)
    normalize.run(extract_result["aligned_path"])

    normalized_segments = read_json(data_dir / "normalized_segments.json", default=[])
    concepts_payload = engine.extract_concepts(
        video_id=ingest_result["video_id"],
        data_dir=data_dir,
        normalized_segments=normalized_segments,
        registry=registry,
        api_key=request.api_key,
    )
    engine.build_graph(
        video_id=ingest_result["video_id"],
        data_dir=data_dir,
        normalized_segments=normalized_segments,
        concepts_payload=concepts_payload,
        registry=registry,
        api_key=request.api_key,
    )

    result = build_result(
        data_dir=data_dir,
        video_id=ingest_result["video_id"],
        url=normalized_url,
        engine=engine_name,
    )
    save_artifacts(result)

    write_json(
        data_dir / "pipeline_summary.json",
        {
            "video_id": result.video.video_id,
            "engine": result.video.engine,
            "concepts": result.stats.concept_count,
            "edges": result.stats.edge_count,
            "learning_path_length": result.stats.learning_path_length,
            "language": result.video.source_language,
        },
    )
    return result


def hydrate_existing_run(*, video_id: str, engine: str = DEFAULT_ENGINE, data_root: str | Path | None = None, api_key: str | None = None) -> LectureGraphResult:
    registry = get_registry()
    selected_engine = registry.get_engine(engine)
    data_dir = resolve_data_root(data_root) / video_id
    watch = normalize_url(video_id)

    bundle_path = data_dir / "lecture2graph.json"
    normalized_path = data_dir / "normalized_segments.json"
    aligned_path = data_dir / "aligned_segments.json"
    if bundle_path.exists() and not normalized_path.exists() and not aligned_path.exists():
        return load_result(video_id, data_root=data_root)

    if not normalized_path.exists():
        from lecture2graph.pipeline import normalize

        if not aligned_path.exists():
            raise FileNotFoundError(f"No normalized or aligned segments found for {video_id}.")
        normalize.run(aligned_path)

    normalized_segments = read_json(normalized_path, default=[])
    concepts_payload = selected_engine.extract_concepts(
        video_id=video_id,
        data_dir=data_dir,
        normalized_segments=normalized_segments,
        registry=registry,
        api_key=api_key,
    )
    selected_engine.build_graph(
        video_id=video_id,
        data_dir=data_dir,
        normalized_segments=normalized_segments,
        concepts_payload=concepts_payload,
        registry=registry,
        api_key=api_key,
    )

    result = build_result(data_dir=data_dir, video_id=video_id, url=watch, engine=engine)
    save_artifacts(result)
    return result


def load_result(video_id: str, data_root: str | Path | None = None) -> LectureGraphResult:
    data_dir = resolve_data_root(data_root) / get_video_id(video_id)
    bundle = read_json(data_dir / "lecture2graph.json")
    if not bundle:
        raise FileNotFoundError(f"No Lecture2Graph bundle found for {video_id}.")
    return LectureGraphResult.model_validate(bundle)
