"""
Regenerate the neural prerequisite graph from *cached* artifacts.

The full neural pipeline (`lecture2graph.neural.pipeline`) downloads the video
and runs Whisper + Tesseract. That is expensive and only needed once. Once a
video's `aligned_segments.json` is cached, the neural extraction is just two
local-LLM calls — so this module re-runs only M3(in-memory)→M4→M5 and writes

    data/<video>/graph.neural.json     (benchmark/fusion input)
    data/<video>/concepts.neural.json  (extracted concepts, for inspection)

without touching the symbolic artifacts that share the data directory. This is
what makes "swap the LLM and re-benchmark all videos" a minutes-long, offline
operation.

usage:
  python -m lecture2graph.neural.from_cache            # all cached videos
  python -m lecture2graph.neural.from_cache XRcC7bAtL3c
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from lecture2graph.neural.normalize import normalize_segments
from lecture2graph.neural.concepts import extract_concepts
from lecture2graph.neural.prereqs import build_prerequisites
from lecture2graph.neural import llm


def run_cached(video_id: str, data_root: str = "data") -> dict:
    base = Path(data_root) / video_id
    aligned = base / "aligned_segments.json"
    if not aligned.exists():
        raise FileNotFoundError(
            f"{aligned} missing — run the full pipeline once to cache it")

    segments = normalize_segments(json.loads(aligned.read_text()))
    concepts = extract_concepts(segments).get("concepts", [])
    graph = build_prerequisites(concepts, segments)

    (base / "concepts.neural.json").write_text(
        json.dumps({"video_id": video_id, "concepts": concepts}, indent=2))
    (base / "graph.neural.json").write_text(json.dumps(graph, indent=2))
    return graph


def main() -> None:
    p = argparse.ArgumentParser(
        description="Regenerate graph.neural.json from cached transcripts via the local LLM")
    p.add_argument("video_id", nargs="?", help="omit to process all cached videos")
    p.add_argument("--data-root", default="data")
    args = p.parse_args()

    root = Path(args.data_root)
    if args.video_id:
        videos = [args.video_id]
    else:
        videos = sorted(d.name for d in root.iterdir()
                        if (d / "aligned_segments.json").exists())

    print(f"[neural.from_cache] model = {llm.model()}  @ {llm.base_url()}")
    failed = []
    for v in videos:
        try:
            g = run_cached(v, args.data_root)
            print(f"[neural.from_cache] {v}: {len(g.get('edges', []))} edges, "
                  f"{len(g.get('topological_order', []))} concepts")
        except Exception as e:  # one bad video must not abort the batch
            failed.append(v)
            print(f"[neural.from_cache] {v}: FAILED — {type(e).__name__}: {e}")
    if failed:
        print(f"[neural.from_cache] {len(failed)} failed: {', '.join(failed)}")


if __name__ == "__main__":
    main()
