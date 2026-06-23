"""
pipeline: neural (LLM-in-the-loop) orchestrator, local model.

Reuses M1 (ingest) and M2 (extract) from the symbolic pipeline, video
download, audio extraction, whisper ASR, and tesseract OCR are identical.

New/replaced modules:
  M3: simplified normalization (LLM handles noisy text gracefully)
  M4: local-LLM concept extraction (semantic, not regex)
  M5: local-LLM prerequisite mapping (reasoned, not hardcoded)

Reuses M6 (visualize) from the symbolic pipeline, same hierarchical DAG.

LLM budget: exactly 2 calls per video (1 for M4 + 1 for M5), against the local
server configured in lecture2graph.neural.llm (Ollama by default).

usage:
  python -m lecture2graph.neural.pipeline <youtube_url>
  # configure the model with LECTURE2GRAPH_LLM_MODEL / _BASE_URL (see neural.llm)
"""

import sys
import json
import time
import argparse
from pathlib import Path

sys.stdout.reconfigure(line_buffering=True)

from lecture2graph.symbolic import ingest as m1_ingest
from lecture2graph.symbolic import extract as m2_extract
from lecture2graph.symbolic import visualize as m6_visualize

from lecture2graph.neural import normalize as m3_normalize
from lecture2graph.neural import concepts as m4_concepts
from lecture2graph.neural import prereqs as m5_prereqs


STAGES = ["m1", "m2", "m3", "m4", "m5", "m6"]


def _banner(stage: str, label: str) -> None:
    ts = time.strftime("%H:%M:%S")
    print(f"\n{'='*60}", flush=True)
    print(f"  [{ts}]  {stage.upper()}, {label}", flush=True)
    print(f"{'='*60}", flush=True)


def _should_run(stage: str, force_from: str | None) -> bool:
    if force_from is None:
        return True
    return STAGES.index(stage) >= STAGES.index(force_from)


def _resolve_data_root(data_root: str) -> str:
    p = Path(data_root)
    if p.exists():
        return str(p)
    alt = _PROJECT_ROOT / data_root
    if alt.exists():
        return str(alt)
    p.mkdir(parents=True, exist_ok=True)
    return str(p)


def run_pipeline(url: str, model: str = "small",
                 data_root: str = "data", force_from: str = None,
                 callback=None) -> dict:
    """
    Run the full neural pipeline on a YouTube video.

    LLM calls: exactly 2 per video (M4 concepts + M5 prereqs), against the
    local model configured in lecture2graph.neural.llm.
    """
    data_root = _resolve_data_root(data_root)
    results = {}
    timings = {}

    def notify(stage, status, info=None):
        if callback:
            callback(stage, status, info or {})

    # ── m1: ingestion  (reused from approach_1) ──
    _banner("m1", "ingestion [approach_1]")
    notify("m1", "start")
    t0 = time.time()
    m1_result = m1_ingest.run(url, data_root=data_root)
    timings["m1"] = round(time.time() - t0, 1)
    results["m1"] = m1_result
    notify("m1", "done", m1_result)
    print(f"[pipeline] m1 done in {timings['m1']}s", flush=True)

    video_id = m1_result["video_id"]
    out_dir = Path(data_root) / video_id

    # ── m2: extraction  (reused from approach_1) ──
    if _should_run("m2", force_from):
        if force_from and STAGES.index(force_from) <= STAGES.index("m2"):
            for f in ["transcript.json", "transcript_original.json",
                       "detected_language.json", "ocr_raw.json",
                       "aligned_segments.json"]:
                p = out_dir / f
                if p.exists():
                    p.unlink()
                    print(f"[pipeline] cleared cache: {f}")

    _banner("m2", "ASR + OCR extraction [approach_1]")
    notify("m2", "start")
    t0 = time.time()
    m2_result = m2_extract.run(
        m1_result["audio_path"],
        m1_result["frames_dir"],
        model_size=model,
    )
    timings["m2"] = round(time.time() - t0, 1)
    results["m2"] = m2_result
    notify("m2", "done", m2_result)
    print(f"[pipeline] m2 done in {timings['m2']}s", flush=True)

    # ── m3: normalization  (approach_2, simplified) ──
    if _should_run("m3", force_from):
        if force_from and STAGES.index(force_from) <= STAGES.index("m3"):
            for f in ["normalized_segments.json"]:
                p = out_dir / f
                if p.exists():
                    p.unlink()

    aligned_path = str(out_dir / "aligned_segments.json")
    _banner("m3", "normalization [approach_2, simplified]")
    notify("m3", "start")
    t0 = time.time()
    m3_result = m3_normalize.run(aligned_path)
    timings["m3"] = round(time.time() - t0, 1)
    results["m3"] = m3_result
    notify("m3", "done", m3_result)
    print(f"[pipeline] m3 done in {timings['m3']}s", flush=True)

    # ── m4: concept extraction  (neural, local LLM) ──
    if _should_run("m4", force_from):
        for f in ["concepts.json"]:
            p = out_dir / f
            if p.exists() and force_from:
                p.unlink()

    _banner("m4", "concept extraction [neural, local LLM]")
    notify("m4", "start")
    t0 = time.time()
    m4_result = m4_concepts.run(video_id, data_root)
    timings["m4"] = round(time.time() - t0, 1)
    results["m4"] = m4_result
    notify("m4", "done", m4_result)
    print(f"[pipeline] m4 done in {timings['m4']}s, "
          f"{m4_result['total_concepts']} concepts", flush=True)

    # ── m5: prerequisites  (neural, local LLM) ──
    if _should_run("m5", force_from):
        for f in ["graph.json"]:
            p = out_dir / f
            if p.exists() and force_from:
                p.unlink()

    _banner("m5", "prerequisite mapping [neural, local LLM]")
    notify("m5", "start")
    t0 = time.time()
    m5_result = m5_prereqs.run(video_id, data_root)
    timings["m5"] = round(time.time() - t0, 1)
    results["m5"] = m5_result
    notify("m5", "done", m5_result)
    print(f"[pipeline] m5 done in {timings['m5']}s, "
          f"{m5_result['total_edges']} edges", flush=True)

    # ── m6: visualization  (reused from the symbolic pipeline) ──
    concepts_path = str(out_dir / "concepts.json")
    prereqs_path = str(out_dir / "graph.json")
    _banner("m6", "visualization [symbolic]")
    notify("m6", "start")
    t0 = time.time()
    m6_result = m6_visualize.run(concepts_path, prereqs_path,
                                 data_dir=str(out_dir))
    timings["m6"] = round(time.time() - t0, 1)
    results["m6"] = m6_result
    notify("m6", "done", m6_result)
    print(f"[pipeline] m6 done in {timings['m6']}s", flush=True)

    # ── summary ──
    summary = {
        "video_id": video_id,
        "approach": "neural_llm_local",
        "data_dir": str(out_dir),
        "detected_language": m2_result.get("detected_language", "unknown"),
        "n_concepts": m6_result.get("n_concepts", 0),
        "n_edges": m6_result.get("n_edges", 0),
        "n_topo": m6_result.get("n_topo", 0),
        "timings": timings,
        "total_time": round(sum(timings.values()), 1),
    }

    summary_path = out_dir / "pipeline_summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)

    notify("done", "done", summary)
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="neural: LLM-in-the-loop pipeline (local model via Ollama / "
                    "any OpenAI-compatible server)"
    )
    parser.add_argument("url", help="YouTube video URL")
    parser.add_argument("--model", default="small",
                        help="whisper model size (tiny/base/small/medium/large)")
    parser.add_argument("--data-root", default="data",
                        help="output directory for data")
    parser.add_argument("--force-from", choices=STAGES, default=None,
                        help="re-run from this stage, clearing caches")
    args = parser.parse_args()

    summary = run_pipeline(args.url, model=args.model,
                           data_root=args.data_root,
                           force_from=args.force_from)

    print("\n" + "=" * 60)
    print(f"  approach:  {summary['approach']}")
    print(f"  video:     {summary['video_id']}")
    print(f"  language:  {summary['detected_language']}")
    print(f"  concepts:  {summary['n_concepts']}")
    print(f"  edges:     {summary['n_edges']}")
    print(f"  topo:      {summary['n_topo']}/{summary['n_concepts']}")
    print(f"  time:      {summary['total_time']}s")
    print(f"  output:    {summary['data_dir']}/graph.html")
