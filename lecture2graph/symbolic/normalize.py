"""
module 3 — text normalization & correction  (v3 — translation-aware)

changes from v2:
  - works with whisper-translated english text (from m2 v2)
  - improved hallucination filter: catches single-word nonsense, body parts,
    off-topic words that whisper hallucinates on weak audio
  - asr-seeded vocabulary + rapidfuzz for ocr correction (unchanged)
  - language tagging now marks original language from detected_language.json
"""

import json
import re
import argparse
from pathlib import Path
from collections import Counter

from rapidfuzz import fuzz, process


# ───────────────── hallucination filter ─────────────────

# words whisper commonly hallucinates on non-english / noisy audio
HALLUCINATION_WORDS = {
    # body parts (common whisper hallucination on telugu/noisy audio)
    "arm", "leg", "palm", "finger", "thumb", "wrist", "elbow", "shoulder",
    "knee", "ankle", "toe", "foot", "hand", "chest", "neck", "head",
    "forehead", "chin", "nose", "ear", "eye", "mouth", "lip", "tongue",
    # political / social (off-topic hallucinations)
    "lgbt", "trump", "biden", "obama", "congress", "parliament",
    "democrat", "republican", "election", "vote",
    # gaming / pop culture
    "bowser", "mario", "zelda", "pokemon", "minecraft",
    # generic filler
    "subscribe", "like", "comment", "share", "bell", "notification",
    "thumbnail", "click",
}

# patterns that indicate whisper is hallucinating (repetitive / nonsensical)
HALLUCINATION_PATTERNS = [
    r'(.{5,}?)\1{3,}',           # same phrase repeated 4+ times
    r'^[\s\.…]+$',               # only dots/ellipsis
    r'^\W+$',                    # only punctuation
    r'^(um|uh|ah|oh|hmm)\s*$',   # only filler words
    r'^(okay|ok|right|yes|no|so|and|but|the|a|is|it|this|that)\s*$',
                                  # single stopword
]


def _is_hallucination(text: str) -> bool:
    """detect if a segment is likely a whisper hallucination."""
    t = text.strip().lower()

    # too short to be useful
    if len(t) < 3:
        return True

    # single word that's a known hallucination
    words = t.split()
    if len(words) == 1 and t in HALLUCINATION_WORDS:
        return True

    # check hallucination patterns
    for pat in HALLUCINATION_PATTERNS:
        if re.match(pat, t, re.IGNORECASE):
            return True

    # mostly non-ascii in what should be translated english
    ascii_chars = sum(1 for c in t if c.isascii())
    if len(t) > 5 and ascii_chars / len(t) < 0.5:
        return True

    return False


# ───────────────── vocabulary + fuzzy correction ─────────────────


def build_vocabulary(asr_segments: list[dict]) -> set[str]:
    """
    extract vocabulary from asr segments.
    since m2v2 produces english translations, this now captures
    english CS terms even from hindi/telugu source audio.
    """
    vocab = set()
    word_freq = Counter()

    for seg in asr_segments:
        text = seg.get("text", "")
        # extract english words (including hyphenated like "b-tree")
        words = re.findall(r"[a-zA-Z][a-zA-Z0-9\-]*[a-zA-Z0-9]|[a-zA-Z]", text)
        for w in words:
            w_lower = w.lower()
            if len(w_lower) >= 2:
                word_freq[w_lower] += 1

    # keep words that appear 2+ times or are long enough to be meaningful
    for word, count in word_freq.items():
        if count >= 2 or len(word) >= 5:
            vocab.add(word)

    return vocab


def _correct_ocr_token(token: str, vocab: set[str],
                       threshold: float = 75.0) -> str:
    """fuzzy-match an ocr token against asr vocabulary."""
    if not token or len(token) < 3:
        return token

    t_lower = token.lower()

    # exact match — no correction needed
    if t_lower in vocab:
        return token

    # fuzzy match against vocabulary
    match = process.extractOne(
        t_lower, vocab,
        scorer=fuzz.ratio,
        score_cutoff=threshold,
    )
    if match:
        corrected = match[0]
        # preserve original casing pattern
        if token[0].isupper():
            corrected = corrected.capitalize()
        return corrected

    return token


def correct_ocr_segments(ocr_segments: list[dict],
                         vocab: set[str]) -> list[dict]:
    """apply fuzzy correction to ocr text using asr-seeded vocabulary."""
    corrected = []
    for seg in ocr_segments:
        text = seg["text"]
        tokens = text.split()
        new_tokens = [_correct_ocr_token(t, vocab) for t in tokens]
        new_text = " ".join(new_tokens)
        corrected.append({**seg, "text": new_text, "text_original": text})
    return corrected


# ───────────────── normalization ─────────────────


def _normalize_text(text: str) -> str:
    """basic text cleanup: collapse whitespace, strip, lowercase."""
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def _tag_language(text: str, detected_lang: str = "en") -> str:
    """
    tag segment language.
    since m2v2 translates everything to english, the ASR segments are
    always english. we tag with the detected source language for reference.
    """
    # check if text has significant non-latin content
    has_devanagari = bool(re.search(r'[\u0900-\u097F]', text))
    has_telugu = bool(re.search(r'[\u0C00-\u0C7F]', text))
    has_latin = bool(re.search(r'[a-zA-Z]{2,}', text))

    if has_devanagari:
        return "hi"
    elif has_telugu:
        return "te"
    elif has_latin:
        return "en"
    else:
        return detected_lang


# ───────────────── main ─────────────────


def run(aligned_path: str) -> dict:
    aligned_path = Path(aligned_path)
    out_dir = aligned_path.parent

    with open(aligned_path) as f:
        segments = json.load(f)

    # read detected language
    detected_lang = "en"
    lang_path = out_dir / "detected_language.json"
    if lang_path.exists():
        with open(lang_path) as f:
            detected_lang = json.load(f).get("language", "en")

    # separate asr and ocr segments
    asr_segs = [s for s in segments if s.get("source") == "asr"]
    ocr_segs = [s for s in segments if s.get("source") == "ocr"]

    print(f"[m3] input: {len(asr_segs)} asr + {len(ocr_segs)} ocr segments")
    print(f"[m3] detected source language: {detected_lang}")

    # build vocabulary from asr (now english thanks to translation)
    vocab = build_vocabulary(asr_segs)
    print(f"[m3] vocabulary size: {len(vocab)} terms")

    # correct ocr using asr vocabulary
    ocr_corrected = correct_ocr_segments(ocr_segs, vocab)
    corrections = sum(1 for o, c in zip(ocr_segs, ocr_corrected)
                      if o["text"] != c["text"])
    print(f"[m3] ocr corrections: {corrections}/{len(ocr_segs)}")

    # filter hallucinations from asr
    asr_filtered = []
    hallucinations = 0
    for seg in asr_segs:
        if _is_hallucination(seg["text"]):
            hallucinations += 1
            continue
        asr_filtered.append(seg)
    print(f"[m3] hallucinations filtered: {hallucinations}/{len(asr_segs)}")

    # normalize all segments
    normalized = []
    for seg in asr_filtered + ocr_corrected:
        text = _normalize_text(seg["text"])
        if not text or len(text) < 3:
            continue

        lang = _tag_language(text, detected_lang)

        normalized.append({
            "start": seg["start"],
            "end": seg["end"],
            "text": text,
            "source": seg.get("source", "unknown"),
            "lang": lang,
            "source_lang": detected_lang,
        })

    # sort by time
    normalized.sort(key=lambda x: x["start"])

    # save
    out_path = out_dir / "normalized_segments.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(normalized, f, ensure_ascii=False, indent=2)

    # save vocab for debugging
    vocab_path = out_dir / "asr_vocabulary.json"
    with open(vocab_path, "w") as f:
        json.dump(sorted(vocab), f, indent=2)

    print(f"[m3] output: {len(normalized)} normalized segments -> {out_path}")

    return {
        "n_input": len(segments),
        "n_output": len(normalized),
        "n_hallucinations": hallucinations,
        "n_ocr_corrections": corrections,
        "vocab_size": len(vocab),
        "detected_language": detected_lang,
        "normalized_path": str(out_path),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("aligned_path")
    args = parser.parse_args()
    print(run(args.aligned_path))
