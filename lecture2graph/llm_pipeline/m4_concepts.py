"""
module 4 — concept extraction via Groq LLM  (LLM pipeline)

WHY LLM:
  the regex pipeline used ~100 handcrafted regex patterns grouped by domain
  (trees, graphs, DBMS, sorting…). This had two problems:
    1. Missed novel topics not in the pattern list
    2. False positives from regex over-matching on common words

  this pipeline sends the full transcript to an LLM and asks it to
  *semantically* identify CS/technical concepts. The LLM:
    - understands context (e.g. "table" in DBMS vs "table" in HTML)
    - handles misspellings and code-mixed language
    - discovers concepts we didn't anticipate in our regex list
    - returns structured JSON with mention counts and timestamps

WHY GROQ (not Gemini):
  Gemini free-tier has aggressive per-minute token/request quotas that
  block batch processing of 5 videos. Groq provides fast inference on
  Llama 3.3 70B with much more generous rate limits.

REQUEST MINIMIZATION:
  We send the ENTIRE transcript in a SINGLE API call. Llama 3.3 70B on
  Groq has a 128k context window — more than enough for a lecture.
  → exactly 1 request per video for concept extraction.
"""

import json
import re
import time
import argparse
from pathlib import Path

from groq import Groq


# ───────────────── config ─────────────────

_MODEL = "llama-3.3-70b-versatile"
_MAX_RETRIES = 4
_RETRY_DELAY = 10

PROJECT_ROOT = Path(__file__).resolve().parents[2]


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
7. Include up to 5 representative mention_details with start time, source, and short excerpt.

RESPOND WITH ONLY valid JSON — no markdown fences, no explanation:
{
  "concepts": [
    {
      "name": "binary_search_tree",
      "mentions": 5,
      "first_seen": 12.5,
      "sources": ["asr", "ocr"],
      "mention_details": [
        {"start": 12.5, "source": "asr", "text": "binary search tree is a data structure"}
      ]
    }
  ]
}"""


# ───────────────── helpers ─────────────────

def _call_groq(client: Groq, system: str, user: str) -> str:
    """Call Groq with retry + exponential backoff."""
    delay = _RETRY_DELAY
    for attempt in range(_MAX_RETRIES):
        try:
            resp = client.chat.completions.create(
                model=_MODEL,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=0.1,
                max_tokens=8000,
                response_format={"type": "json_object"},
            )
            return resp.choices[0].message.content
        except Exception as e:
            err = str(e)
            if "rate_limit" in err.lower() or "429" in err:
                print(f"[m4] rate limited (attempt {attempt+1}/{_MAX_RETRIES}), "
                      f"waiting {delay}s...")
                time.sleep(delay)
                delay *= 2
            else:
                raise
    raise RuntimeError(f"[m4] Groq failed after {_MAX_RETRIES} retries")


def _parse_json(text: str) -> dict:
    """Extract JSON from LLM response."""
    text = re.sub(r'^```(?:json)?\s*', '', text.strip())
    text = re.sub(r'\s*```$', '', text.strip())
    return json.loads(text)


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

def extract_concepts(segments: list[dict], api_key: str) -> dict:
    """
    Send full transcript to Groq in ONE call, extract concepts.
    Returns: {"concepts": [...]}
    """
    client = Groq(api_key=api_key)
    transcript_text = _format_transcript(segments)
    n_chars = len(transcript_text)

    user_prompt = (
        f"Here is the full transcript of a CS lecture "
        f"({len(segments)} segments, {n_chars} chars).\n"
        f"Each line: [timestamp|source] text  (source: a=speech, o=screen OCR)\n\n"
        f"TRANSCRIPT:\n{transcript_text}\n\n"
        f"Extract ALL CS/technical concepts mentioned. Return ONLY valid JSON."
    )

    print(f"[m4] sending {len(segments)} segments ({n_chars} chars) "
          f"to Groq ({_MODEL})...")

    raw = _call_groq(client, _SYSTEM_PROMPT, user_prompt)

    try:
        result = _parse_json(raw)
        n = len(result.get("concepts", []))
        print(f"[m4] extracted {n} concepts")
        return result
    except json.JSONDecodeError as e:
        print(f"[m4] WARNING: invalid JSON from Groq: {e}")
        print(f"[m4] raw (first 300 chars): {raw[:300]}")
        return {"concepts": []}


# ───────────────── run ─────────────────

def run(video_id: str, data_root: str, api_key: str = None) -> dict:
    """
    Extract concepts for a video using Groq LLM.

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
        if not api_key:
            api_key = _load_api_key(data_dir)
        result = extract_concepts(segments, api_key)

    with open(concepts_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    n = len(result.get("concepts", []))
    print(f"[m4] saved {n} concepts → {concepts_path}")
    return {"total_concepts": n, "concepts_path": str(concepts_path)}


def _load_api_key(data_dir: Path) -> str:
    """Try loading API key from env var or .env file."""
    import os
    key = os.environ.get("GROQ_API_KEY")
    if key:
        return key
    for p in [PROJECT_ROOT / ".env", data_dir.parent / ".env", data_dir.parent.parent / ".env"]:
        if p.exists():
            for line in p.read_text().splitlines():
                if line.startswith("GROQ_API_KEY="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise ValueError("[m4] No API key — set GROQ_API_KEY env var or pass api_key=")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("video_id")
    parser.add_argument("--data-root", default="outputs/llm")
    parser.add_argument("--api-key", default=None)
    args = parser.parse_args()
    print(run(args.video_id, args.data_root, args.api_key))
