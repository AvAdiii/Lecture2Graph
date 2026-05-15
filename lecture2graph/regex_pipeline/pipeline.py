"""
pipeline — orchestrates M1 through M6 for a single YouTube video.

usage:
  python -m lecture2graph.regex_pipeline.pipeline <youtube_url> \
    [--model small] [--data-root outputs/regex] [--force-from m2]
"""

import sys
import json
import time
import argparse
from pathlib import Path

sys.stdout.reconfigure(line_buffering=True)

from . import m1_ingest
from . import m2_extract
from . import m3_normalize
from . import m4_concepts
from . import m5_prereqs
from . import m6_visualize


PROJECT_ROOT = Path(__file__).resolve().parents[2]


STAGES = ["m1", "m2", "m3", "m4", "m5", "m6"]


def _banner(stage: str, label: str) -> None:
    ts = time.strftime("%H:%M:%S")
    print(f"\n{'='*60}", flush=True)
    print(f"  [{ts}]  {stage.upper()} — {label}", flush=True)
    print(f"{'='*60}", flush=True)


def _should_run(stage: str, force_from: str | None) -> bool:
    if force_from is None:
        return True
    return STAGES.index(stage) >= STAGES.index(force_from)


def _resolve_data_root(data_root: str) -> str:
    """Resolve data root — check cwd first, then relative to repo root."""
    p = Path(data_root)
    if p.exists():
        return str(p)
    alt = PROJECT_ROOT / data_root
    if alt.exists():
        return str(alt)
    # create it
    p.mkdir(parents=True, exist_ok=True)
    return str(p)


def run_pipeline(url: str, model: str = "small",
                 data_root: str = "outputs/regex", force_from: str = None,
                 callback=None) -> dict:
    """
    run the full pipeline on a youtube video.

    args:
        url: youtube video url
        model: whisper model size
        data_root: directory for output data
        force_from: re-run from this stage onwards (m1-m6)
        callback: optional fn(stage, status, info) for progress reporting

    returns: dict with all pipeline results
    """
    data_root = _resolve_data_root(data_root)
    results = {}
    timings = {}

    def notify(stage, status, info=None):
        if callback:
            callback(stage, status, info or {})

    # ── m1: ingestion ──
    _banner("m1", "ingestion")
    notify("m1", "start")
    t0 = time.time()
    try:
        m1_result = m1_ingest.run(url, data_root=data_root)
        timings["m1"] = round(time.time() - t0, 1)
        results["m1"] = m1_result
        notify("m1", "done", m1_result)
    except Exception as e:
        notify("m1", "error", {"error": str(e)})
        raise

    video_id = m1_result["video_id"]
    out_dir = Path(data_root) / video_id

    # ── m2: extraction ──
    if _should_run("m2", force_from):
        # clear downstream caches when forcing from m2
        if force_from and STAGES.index(force_from) <= STAGES.index("m2"):
            for f in ["transcript.json", "transcript_original.json",
                       "detected_language.json", "ocr_raw.json",
                       "aligned_segments.json"]:
                p = out_dir / f
                if p.exists():
                    p.unlink()
                    print(f"[pipeline] cleared cache: {f}")

    _banner("m2", "ASR + OCR extraction")
    notify("m2", "start")
    t0 = time.time()
    try:
        m2_result = m2_extract.run(
            m1_result["audio_path"],
            m1_result["frames_dir"],
            model_size=model,
        )
        timings["m2"] = round(time.time() - t0, 1)
        results["m2"] = m2_result
        notify("m2", "done", m2_result)
        print(f"[pipeline] m2 done in {timings['m2']}s", flush=True)
    except Exception as e:
        notify("m2", "error", {"error": str(e)})
        raise

    # ── m3: normalization ──
    if _should_run("m3", force_from):
        if force_from and STAGES.index(force_from) <= STAGES.index("m3"):
            for f in ["normalized_segments.json", "asr_vocabulary.json"]:
                p = out_dir / f
                if p.exists():
                    p.unlink()

    aligned_path = str(out_dir / "aligned_segments.json")
    _banner("m3", "normalization")
    notify("m3", "start")
    t0 = time.time()
    try:
        m3_result = m3_normalize.run(aligned_path)
        timings["m3"] = round(time.time() - t0, 1)
        results["m3"] = m3_result
        notify("m3", "done", m3_result)
        print(f"[pipeline] m3 done in {timings['m3']}s", flush=True)
    except Exception as e:
        notify("m3", "error", {"error": str(e)})
        raise

    # ── m4: concepts ──
    if _should_run("m4", force_from):
        for f in ["concepts.json"]:
            p = out_dir / f
            if p.exists() and force_from:
                p.unlink()

    _banner("m4", "concept extraction")
    notify("m4", "start")
    t0 = time.time()
    try:
        m4_result = m4_concepts.run(video_id, data_root)
        timings["m4"] = round(time.time() - t0, 1)
        results["m4"] = m4_result
        notify("m4", "done", m4_result)
        print(f"[pipeline] m4 done in {timings['m4']}s — {m4_result['total_concepts']} concepts", flush=True)
    except Exception as e:
        notify("m4", "error", {"error": str(e)})
        raise

    # ── m5: prerequisites ──
    if _should_run("m5", force_from):
        for f in ["graph.json"]:
            p = out_dir / f
            if p.exists() and force_from:
                p.unlink()

    concepts_path = str(out_dir / "concepts.json")
    _banner("m5", "prerequisite mapping")
    notify("m5", "start")
    t0 = time.time()
    try:
        m5_result = m5_prereqs.run(video_id, data_root)
        timings["m5"] = round(time.time() - t0, 1)
        results["m5"] = m5_result
        notify("m5", "done", m5_result)
        print(f"[pipeline] m5 done in {timings['m5']}s — {m5_result['total_edges']} edges", flush=True)
    except Exception as e:
        notify("m5", "error", {"error": str(e)})
        raise

    # ── m6: visualization ──
    _banner("m6", "visualization")
    prereqs_path = str(out_dir / "graph.json")
    notify("m6", "start")
    t0 = time.time()
    try:
        m6_result = m6_visualize.run(concepts_path, prereqs_path,
                                     data_dir=str(out_dir))
        timings["m6"] = round(time.time() - t0, 1)
        results["m6"] = m6_result
        notify("m6", "done", m6_result)
        print(f"[pipeline] m6 done in {timings['m6']}s", flush=True)
    except Exception as e:
        notify("m6", "error", {"error": str(e)})
        raise

    # ── summary ──
    summary = {
        "video_id": video_id,
        "data_dir": str(out_dir),
        "detected_language": m2_result.get("detected_language", "unknown"),
        "n_concepts": m6_result.get("n_concepts", 0),
        "n_edges": m6_result.get("n_edges", 0),
        "n_topo": m6_result.get("n_topo", 0),
        "timings": timings,
        "total_time": round(sum(timings.values()), 1),
    }

    # save summary
    summary_path = out_dir / "pipeline_summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)

    notify("done", "done", summary)
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="run the concept extraction pipeline on a youtube video"
    )
    parser.add_argument("url", help="youtube video url")
    parser.add_argument("--model", default="small",
                        help="whisper model size (tiny/base/small/medium/large)")
    parser.add_argument("--data-root", default="outputs/regex",
                        help="output directory for data")
    parser.add_argument("--force-from", choices=STAGES, default=None,
                        help="re-run from this stage, clearing caches")
    args = parser.parse_args()

    summary = run_pipeline(args.url, model=args.model,
                           data_root=args.data_root,
                           force_from=args.force_from)

    print("\n" + "=" * 60)
    print(f"  video:    {summary['video_id']}")
    print(f"  language: {summary['detected_language']}")
    print(f"  concepts: {summary['n_concepts']}")
    print(f"  edges:    {summary['n_edges']}")
    print(f"  topo:     {summary['n_topo']}/{summary['n_concepts']}")
    print(f"  time:     {summary['total_time']}s")
    print(f"  output:   {summary['data_dir']}/graph.html")
    print("=" * 60)
