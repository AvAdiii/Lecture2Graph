#!/usr/bin/env python
"""
Run the LLM pipeline (Groq) on all 5 test videos.

Reuses M1/M2 artifacts from the regex pipeline outputs by symlinking.
Only M3-M6 run fresh.

API budget: 2 Groq calls per video × 5 videos = 10 total API calls.
"""

import sys
import os
import time
from pathlib import Path

sys.stdout.reconfigure(line_buffering=True)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from lecture2graph.llm_pipeline import m3_normalize
from lecture2graph.llm_pipeline import m4_concepts
from lecture2graph.llm_pipeline import m5_prereqs
from lecture2graph.regex_pipeline import m6_visualize


def load_dotenv(dotenv_path: Path) -> None:
    """Lightweight .env loader (no external dependency)."""
    if not dotenv_path.exists():
        return

    for line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


load_dotenv(PROJECT_ROOT / ".env")
API_KEY = os.getenv("GROQ_API_KEY", "").strip()

# the 5 test videos
VIDEOS = [
    "XRcC7bAtL3c",   # English — tree data structures
    "N2P7w22tN9c",   # English — BFS/DFS graph traversal
    "Tp37HXfekNo",   # Hindi   — DBMS keys
    "azXr6nTaD9M",   # Hindi   — CS concepts
    "eXWl-Uor75o",   # Telugu  — sorting / merge sort
]

# M1/M2 artifacts to symlink
M1M2_FILES = [
    "video.mp4", "audio.wav", "frames",
    "transcript.json", "transcript_original.json",
    "detected_language.json", "ocr_raw.json", "aligned_segments.json",
]

OUTPUT_ROOT = PROJECT_ROOT / "outputs"
SRC_DATA = OUTPUT_ROOT / "regex"
DST_DATA = OUTPUT_ROOT / "llm"


def symlink_m1m2(video_id: str):
    """Symlink M1/M2 artifacts from regex pipeline output."""
    src_dir = SRC_DATA / video_id
    dst_dir = DST_DATA / video_id
    dst_dir.mkdir(parents=True, exist_ok=True)
    for name in M1M2_FILES:
        src = src_dir / name
        dst = dst_dir / name
        if src.exists() and not dst.exists():
            dst.symlink_to(src.resolve())
            print(f"  symlinked: {name}")


def run_video(video_id: str):
    """Run M3→M6 for one video."""
    data_dir = DST_DATA / video_id
    ts = time.strftime("%H:%M:%S")

    print(f"\n{'#'*70}")
    print(f"  [{ts}]  {video_id}")
    print(f"{'#'*70}\n")

    symlink_m1m2(video_id)

    # clear old LLM outputs
    for f in ["normalized_segments.json", "concepts.json",
              "graph.json", "graph.html", "report.md",
              "pipeline_summary.json", "asr_vocabulary.json"]:
        p = data_dir / f
        if p.exists() and not p.is_symlink():
            p.unlink()

    # M3
    print("--- M3: normalization ---")
    t0 = time.time()
    m3_result = m3_normalize.run(str(data_dir / "aligned_segments.json"))
    print(f"  {time.time()-t0:.1f}s — {m3_result['n_segments']} segments\n")

    # M4 — 1 API call
    print("--- M4: Groq concept extraction (1 API call) ---")
    t0 = time.time()
    m4_result = m4_concepts.run(video_id, str(DST_DATA), api_key=API_KEY)
    print(f"  {time.time()-t0:.1f}s — {m4_result['total_concepts']} concepts\n")

    # M5 — 1 API call
    print("--- M5: Groq prerequisite mapping (1 API call) ---")
    t0 = time.time()
    m5_result = m5_prereqs.run(video_id, str(DST_DATA), api_key=API_KEY)
    print(f"  {time.time()-t0:.1f}s — {m5_result['total_edges']} edges\n")

    # M6
    print("--- M6: visualization ---")
    t0 = time.time()
    m6_result = m6_visualize.run(
        str(data_dir / "concepts.json"),
        str(data_dir / "graph.json"),
        data_dir=str(data_dir),
    )
    print(f"  {time.time()-t0:.1f}s\n")

    return {
        "video_id": video_id,
        "n_concepts": m6_result.get("n_concepts", 0),
        "n_edges": m6_result.get("n_edges", 0),
        "n_topo": m6_result.get("n_topo", 0),
    }


def main():
    if not API_KEY:
        raise RuntimeError(
            "Missing GROQ_API_KEY. Add it to .env or export GROQ_API_KEY in your shell."
        )

    t_start = time.time()
    print("=" * 70)
    print("  llm pipeline — Groq / Llama 3.3 70B")
    print(f"  {len(VIDEOS)} videos | 2 API calls each | 10 total")
    print("=" * 70)

    results = []
    for vid in VIDEOS:
        try:
            r = run_video(vid)
            results.append(r)
        except Exception as e:
            print(f"\n!!! ERROR on {vid}: {e}")
            import traceback
            traceback.print_exc()
            results.append({"video_id": vid, "error": str(e)})

    elapsed = time.time() - t_start

    print("\n" + "=" * 70)
    print("  SUMMARY")
    print("=" * 70)
    print(f"  {'Video':<15} {'Concepts':>8} {'Edges':>8} {'Topo':>8}")
    print(f"  {'-'*15} {'-'*8} {'-'*8} {'-'*8}")
    for r in results:
        if "error" in r:
            print(f"  {r['video_id']:<15} {'ERROR':>8}   {r['error'][:30]}")
        else:
            print(f"  {r['video_id']:<15} {r['n_concepts']:>8} "
                  f"{r['n_edges']:>8} {r['n_topo']:>8}")
    print(f"\n  Total time: {elapsed:.1f}s")
    print(f"  Output: {DST_DATA}/*/graph.html")


if __name__ == "__main__":
    main()
