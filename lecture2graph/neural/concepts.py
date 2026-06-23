"""
module 4 (neural) — concept extraction via a local LLM.

WHY LLM:
  The symbolic pipeline used ~100 handcrafted regex patterns grouped by domain
  (trees, graphs, DBMS, sorting…). This had two problems:
    1. Missed novel topics not in the pattern list
    2. False positives from regex over-matching on common words

  This module sends the full transcript to an LLM and asks it to
  *semantically* identify CS/technical concepts. The LLM:
    - understands context (e.g. "table" in DBMS vs "table" in HTML)
    - handles misspellings and code-mixed language
    - discovers concepts we didn't anticipate in our regex list
    - returns structured JSON with mention counts and timestamps

LOCAL, NOT CLOUD:
  Inference runs against a local OpenAI-compatible server (Ollama by default —
  see lecture2graph.neural.llm). No API key, no rate limits, no data leaves the
  machine — so the whole corpus can be re-processed freely.

REQUEST MINIMIZATION:
  The ENTIRE transcript goes in a SINGLE call (one request per video).
"""

import json
import argparse
from pathlib import Path

from lecture2graph.neural import llm


# ───────────────── prompt ─────────────────

_SYSTEM_PROMPT = """\
You are an expert computer science educator analyzing a lecture transcript.
Your job: extract every distinct CS / technical concept taught in this lecture.

RULES:
1. Only extract CS, programming, data structure, algorithm, database, or math concepts.
   Do NOT include: people's names, course names, YouTube channel names,
   generic English words, lecture navigation ("next slide", "let's see").
2. Normalize concept names to canonical snake_case (e.g. "binary_search_tree",
   "depth_first_search", "primary_key", "merge_sort").
3. Merge synonyms: e.g. "BST" and "binary search tree" → "binary_search_tree".
4. For each concept, count how many transcript segments mention it.
5. Record the earliest timestamp (start field) where it appears as first_seen.
6. List which sources mentioned it (asr, ocr, or both).

RESPOND WITH ONLY valid JSON — no markdown fences, no explanation:
{
  "concepts": [
    {
      "name": "binary_search_tree",
      "mentions": 5,
      "first_seen": 12.5,
      "sources": ["asr", "ocr"]
    }
  ]
}"""

# Chunk the transcript so a long lecture never overflows the local model's
# context window (input + JSON output must both fit). ~8k chars ≈ 2k tokens,
# leaving ample room for the system prompt and the generated JSON.
_CHUNK_CHARS = 8000


# ───────────────── helpers ─────────────────

def _format_transcript(segments: list[dict]) -> str:
    """Format segments compactly for the LLM prompt."""
    lines = []
    for seg in segments:
        t = seg.get("start", 0)
        src = seg.get("source", "?")[0]   # a=asr, o=ocr — saves tokens
        text = seg.get("text", "").strip()
        if len(text) > 150:
            text = text[:147] + "..."
        lines.append(f"[{t:.0f}s|{src}] {text}")
    return "\n".join(lines)


# ───────────────── core ─────────────────

def _chunk_segments(segments: list[dict]) -> list[list[dict]]:
    """Split segments into chunks whose formatted text stays under _CHUNK_CHARS."""
    chunks, cur, cur_len = [], [], 0
    for seg in segments:
        line_len = len(seg.get("text", "")) + 16  # ~timestamp/source overhead
        if cur and cur_len + line_len > _CHUNK_CHARS:
            chunks.append(cur)
            cur, cur_len = [], 0
        cur.append(seg)
        cur_len += line_len
    if cur:
        chunks.append(cur)
    return chunks


def _merge_concepts(parts: list[dict]) -> list[dict]:
    """Union concepts across chunks: sum mentions, keep earliest first_seen."""
    merged: dict[str, dict] = {}
    for p in parts:
        for c in p.get("concepts", []):
            name = str(c.get("name", "")).strip()
            if not name:
                continue
            fs = c.get("first_seen", c.get("first_mention"))
            fs = float(fs) if isinstance(fs, (int, float)) else None
            if name not in merged:
                merged[name] = {"name": name, "mentions": c.get("mentions", 1) or 1,
                                "first_seen": fs, "sources": list(c.get("sources", []) or [])}
            else:
                m = merged[name]
                m["mentions"] += c.get("mentions", 1) or 1
                if fs is not None and (m["first_seen"] is None or fs < m["first_seen"]):
                    m["first_seen"] = fs
                m["sources"] = sorted(set(m["sources"]) | set(c.get("sources", []) or []))
    return list(merged.values())


def _extract_one(segments: list[dict]) -> dict:
    transcript_text = _format_transcript(segments)
    user_prompt = (
        f"Here is part of a CS lecture transcript "
        f"({len(segments)} segments, {len(transcript_text)} chars).\n"
        f"Each line: [timestamp|source] text  (source: a=speech, o=screen OCR)\n\n"
        f"TRANSCRIPT:\n{transcript_text}\n\n"
        f"Extract ALL CS/technical concepts mentioned. Return ONLY valid JSON."
    )
    raw = llm.chat(_SYSTEM_PROMPT, user_prompt, temperature=0.1)
    try:
        return llm.extract_json(raw)
    except json.JSONDecodeError as e:
        print(f"[m4] WARNING: invalid JSON from LLM: {e}")
        return {"concepts": []}


def extract_concepts(segments: list[dict]) -> dict:
    """
    Extract concepts from the transcript via the local LLM.

    Long lectures are chunked (map) and the per-chunk concept lists are merged
    (reduce), so an arbitrarily long transcript never overflows the model's
    context window. Returns: {"concepts": [...]}
    """
    chunks = _chunk_segments(segments)
    n_chars = sum(len(s.get("text", "")) for s in segments)
    print(f"[m4] {len(segments)} segments (~{n_chars} chars) -> {len(chunks)} "
          f"chunk(s) to local LLM ({llm.model()})...")

    parts = [_extract_one(ch) for ch in chunks]
    concepts = _merge_concepts(parts)
    print(f"[m4] extracted {len(concepts)} concepts")
    return {"concepts": concepts}


# ───────────────── run ─────────────────

def run(video_id: str, data_root: str) -> dict:
    """
    Extract concepts for a video using the local LLM.

    Reads:  data_root/video_id/normalized_segments.json
    Writes: data_root/video_id/concepts.json
    Returns: {"total_concepts": N, "concepts_path": "..."}
    """
    data_dir = Path(data_root) / video_id
    norm_path = data_dir / "normalized_segments.json"
    concepts_path = data_dir / "concepts.json"

    # cache check
    if concepts_path.exists():
        with open(concepts_path) as f:
            existing = json.load(f)
        n = len(existing.get("concepts", []))
        print(f"[m4] using cached concepts: {n} concepts")
        return {"total_concepts": n, "concepts_path": str(concepts_path)}

    if not norm_path.exists():
        raise FileNotFoundError(f"[m4] {norm_path} not found — run M3 first")

    with open(norm_path) as f:
        segments = json.load(f)

    if not segments:
        print("[m4] no segments to extract concepts from")
        result = {"concepts": []}
    else:
        result = extract_concepts(segments)

    with open(concepts_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    n = len(result.get("concepts", []))
    print(f"[m4] saved {n} concepts → {concepts_path}")
    return {"total_concepts": n, "concepts_path": str(concepts_path)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("video_id")
    parser.add_argument("--data-root", default="data")
    args = parser.parse_args()
    print(run(args.video_id, args.data_root))
