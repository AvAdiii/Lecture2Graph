"""
module 3 — simplified text normalization  (LLM pipeline)

WHY SIMPLIFIED:
  regex pipeline m3 did heavy regex cleaning, fuzzy OCR correction, and
  hallucination filtering because the downstream regex patterns were fragile.

  the LLM pipeline sends text to a Groq-hosted LLM which can handle:
  - misspelled words (e.g. "recurson" → understands as "recursion")
  - code-mixed speech (e.g. hindi+english)
  - noisy OCR (e.g. "B1nary Tr33" → understands as "Binary Tree")
  - filler words and partial sentences

  so we only need basic cleanup here:
  1. merge ASR + OCR segments chronologically
  2. remove extreme hallucinations (repeated text, empty segments)
  3. tag source (asr/ocr) and language
  4. output clean segments for the LLM to consume
"""

import json
import re
import argparse
from pathlib import Path


# ───────────────── minimal hallucination filter ─────────────────

def _is_garbage(text: str) -> bool:
    """catch only the most obvious garbage — LLM handles the rest."""
    t = text.strip()
    if len(t) < 2:
        return True
    # only punctuation / whitespace
    if not re.search(r'[a-zA-Z0-9\u0900-\u0D7F]', t):
        return True
    # same phrase repeated 4+ times
    if re.search(r'(.{5,}?)\1{3,}', t):
        return True
    return False


# ───────────────── main ─────────────────

def run(aligned_path: str) -> dict:
    """
    Light normalization of aligned ASR+OCR segments.

    Input:  aligned_segments.json  (from M2)
    Output: normalized_segments.json  (cleaned, tagged)

    Returns dict with stats.
    """
    aligned_path = Path(aligned_path)
    out_dir = aligned_path.parent

    with open(aligned_path) as f:
        segments = json.load(f)

    # load language metadata
    lang_path = out_dir / "detected_language.json"
    source_lang = "en"
    if lang_path.exists():
        with open(lang_path) as f:
            source_lang = json.load(f).get("language", "en")

    cleaned = []
    n_dropped = 0
    prev_text = ""

    # handle both old format (spoken_text/visual_text) and
    # new format (text/source) from different M2 versions
    expanded = []
    for seg in segments:
        if "text" in seg and "source" in seg:
            # new format — already one segment per source
            expanded.append(seg)
        else:
            # old format — split into asr + ocr segments
            spoken = seg.get("spoken_text", "").strip()
            visual = seg.get("visual_text", "").strip()
            if spoken:
                expanded.append({
                    "start": seg.get("start", 0),
                    "end": seg.get("end", 0),
                    "text": spoken,
                    "source": "asr",
                })
            if visual:
                expanded.append({
                    "start": seg.get("start", 0),
                    "end": seg.get("end", 0),
                    "text": visual,
                    "source": "ocr",
                })

    for seg in expanded:
        text = seg.get("text", "").strip()

        # drop garbage
        if _is_garbage(text):
            n_dropped += 1
            continue

        # basic whitespace normalization
        text = re.sub(r'\s+', ' ', text).strip()

        # dedup consecutive identical text
        if text.lower() == prev_text.lower():
            n_dropped += 1
            continue
        prev_text = text

        cleaned.append({
            "start": seg.get("start", 0),
            "end": seg.get("end", 0),
            "text": text,
            "source": seg.get("source", "unknown"),
            "lang": "en",           # whisper translate mode → always english
            "source_lang": source_lang,
        })

    # save
    out_path = out_dir / "normalized_segments.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(cleaned, f, ensure_ascii=False, indent=2)

    print(f"[m3] normalized {len(cleaned)} segments "
          f"(dropped {n_dropped} garbage/dupes)")

    return {
        "n_segments": len(cleaned),
        "n_dropped": n_dropped,
        "source_lang": source_lang,
        "output_path": str(out_path),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("aligned_path")
    args = parser.parse_args()
    print(run(args.aligned_path))
