"""Normalize segments and clean OCR noise."""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

from rapidfuzz import fuzz, process

from lecture2graph.utils.io import read_json, write_json


HALLUCINATION_WORDS = {
    "arm", "leg", "palm", "finger", "thumb", "wrist", "elbow", "shoulder",
    "knee", "ankle", "toe", "foot", "hand", "chest", "neck", "head",
    "forehead", "chin", "nose", "ear", "eye", "mouth", "lip", "tongue",
    "lgbt", "trump", "biden", "obama", "congress", "parliament",
    "democrat", "republican", "election", "vote",
    "bowser", "mario", "zelda", "pokemon", "minecraft",
    "subscribe", "like", "comment", "share", "bell", "notification",
    "thumbnail", "click",
}

HALLUCINATION_PATTERNS = [
    r"(.{5,}?)\1{3,}",
    r"^[\s\.…]+$",
    r"^\W+$",
    r"^(um|uh|ah|oh|hmm)\s*$",
    r"^(okay|ok|right|yes|no|so|and|but|the|a|is|it|this|that)\s*$",
]


def _is_hallucination(text: str) -> bool:
    cleaned = text.strip().lower()
    if len(cleaned) < 3:
        return True
    if len(cleaned.split()) == 1 and cleaned in HALLUCINATION_WORDS:
        return True
    if any(re.match(pattern, cleaned, re.IGNORECASE) for pattern in HALLUCINATION_PATTERNS):
        return True
    ascii_chars = sum(1 for character in cleaned if character.isascii())
    if len(cleaned) > 5 and ascii_chars / len(cleaned) < 0.5:
        return True
    return False


def build_vocabulary(asr_segments: list[dict]) -> set[str]:
    frequencies = Counter()
    for segment in asr_segments:
        words = re.findall(r"[a-zA-Z][a-zA-Z0-9\-]*[a-zA-Z0-9]|[a-zA-Z]", segment.get("text", ""))
        for word in words:
            lowered = word.lower()
            if len(lowered) >= 2:
                frequencies[lowered] += 1
    return {word for word, count in frequencies.items() if count >= 2 or len(word) >= 5}


def _correct_ocr_token(token: str, vocabulary: set[str], threshold: float = 75.0) -> str:
    if not token or len(token) < 3:
        return token
    lowered = token.lower()
    if lowered in vocabulary:
        return token
    match = process.extractOne(lowered, vocabulary, scorer=fuzz.ratio, score_cutoff=threshold)
    if not match:
        return token
    corrected = match[0]
    return corrected.capitalize() if token[:1].isupper() else corrected


def correct_ocr_segments(ocr_segments: list[dict], vocabulary: set[str]) -> list[dict]:
    corrected_segments = []
    for segment in ocr_segments:
        updated_text = " ".join(_correct_ocr_token(token, vocabulary) for token in segment["text"].split())
        corrected_segments.append({**segment, "text": updated_text, "text_original": segment["text"]})
    return corrected_segments


def _tag_language(text: str, detected_language: str) -> str:
    if re.search(r"[\u0900-\u097F]", text):
        return "hi"
    if re.search(r"[\u0C00-\u0C7F]", text):
        return "te"
    if re.search(r"[a-zA-Z]{2,}", text):
        return "en"
    return detected_language


def run(aligned_path: str | Path) -> dict:
    aligned_file = Path(aligned_path)
    out_dir = aligned_file.parent

    segments = read_json(aligned_file, default=[])
    detected_language = read_json(out_dir / "detected_language.json", default={"language": "en"}).get("language", "en")

    asr_segments = [segment for segment in segments if segment.get("source") == "asr"]
    ocr_segments = [segment for segment in segments if segment.get("source") == "ocr"]

    vocabulary = build_vocabulary(asr_segments)
    corrected_ocr = correct_ocr_segments(ocr_segments, vocabulary)

    normalized_segments = []
    hallucination_count = 0
    for segment in asr_segments:
        if _is_hallucination(segment["text"]):
            hallucination_count += 1
            continue
        normalized_segments.append(segment)

    normalized_segments.extend(corrected_ocr)
    cleaned_segments = []
    for segment in normalized_segments:
        text = re.sub(r"\s+", " ", segment["text"]).strip()
        if len(text) < 3:
            continue
        cleaned_segments.append(
            {
                "start": segment["start"],
                "end": segment["end"],
                "text": text,
                "source": segment.get("source", "unknown"),
                "lang": _tag_language(text, detected_language),
                "source_lang": detected_language,
            }
        )

    cleaned_segments.sort(key=lambda item: item["start"])
    normalized_path = out_dir / "normalized_segments.json"
    vocabulary_path = out_dir / "asr_vocabulary.json"
    write_json(normalized_path, cleaned_segments)
    write_json(vocabulary_path, sorted(vocabulary))

    return {
        "normalized_path": str(normalized_path),
        "detected_language": detected_language,
        "vocab_size": len(vocabulary),
        "n_input": len(segments),
        "n_output": len(cleaned_segments),
        "n_hallucinations": hallucination_count,
    }

