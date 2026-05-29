"""ASR, OCR, and transcript alignment."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytesseract
import whisper
from PIL import Image

from lecture2graph.utils.io import read_json, write_json


def detect_language(model, audio_path: Path) -> tuple[str, float]:
    audio = whisper.load_audio(str(audio_path))
    audio_30s = whisper.pad_or_trim(audio)
    mel = whisper.log_mel_spectrogram(audio_30s).to(model.device)
    _, probabilities = model.detect_language(mel)
    language = max(probabilities, key=probabilities.get)
    return language, probabilities[language]


def run_asr(audio_path: Path, model_size: str = "small") -> tuple[list[dict], dict]:
    transcript_path = audio_path.parent / "transcript.json"
    original_path = audio_path.parent / "transcript_original.json"
    language_path = audio_path.parent / "detected_language.json"

    cached_translated = read_json(transcript_path)
    cached_language = read_json(language_path)
    if cached_translated and cached_language:
        return cached_translated, cached_language

    model = whisper.load_model(model_size)
    language, confidence = detect_language(model, audio_path)
    language_payload = {"language": language, "confidence": round(confidence, 4)}
    write_json(language_path, language_payload)

    original = model.transcribe(str(audio_path), task="transcribe", verbose=False)
    original_segments = [
        {"start": item["start"], "end": item["end"], "text": item["text"].strip(), "source": "asr"}
        for item in original["segments"]
    ]
    write_json(original_path, original_segments)

    if language != "en":
        translated = model.transcribe(str(audio_path), task="translate", verbose=False)
        translated_segments = [
            {"start": item["start"], "end": item["end"], "text": item["text"].strip(), "source": "asr"}
            for item in translated["segments"]
        ]
    else:
        translated_segments = original_segments

    write_json(transcript_path, translated_segments)
    return translated_segments, language_payload


def _clean_ocr(text: str) -> str:
    text = re.sub(r"[^\w\s\-\>\<\=\+\(\)\[\]\{\}\.\,\;\:\'\"]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _ocr_confidence(frame_path: Path) -> tuple[str, float]:
    image = Image.open(frame_path)
    data = pytesseract.image_to_data(
        image,
        lang="eng+hin",
        output_type=pytesseract.Output.DICT,
    )

    words: list[str] = []
    confidences: list[int] = []
    for word, confidence in zip(data["text"], data["conf"]):
        score = int(confidence) if str(confidence).lstrip("-").isdigit() else -1
        if score > 0 and word.strip():
            words.append(word.strip())
            confidences.append(score)

    if not confidences:
        return "", 0.0
    return " ".join(words), sum(confidences) / len(confidences)


def _pick_best_ocr(frame_path: Path, iterations: int = 3) -> tuple[str, float]:
    best_text = ""
    best_confidence = 0.0
    for _ in range(iterations):
        text, confidence = _ocr_confidence(frame_path)
        if confidence > best_confidence:
            best_text = text
            best_confidence = confidence
    return best_text, best_confidence


def run_ocr(frames_dir: Path, min_confidence: float = 40.0) -> list[dict]:
    ocr_path = frames_dir.parent / "ocr_raw.json"
    cached = read_json(ocr_path)
    if cached:
        return cached

    segments: list[dict] = []
    previous_text = ""
    for frame_path in sorted(frames_dir.glob("*.jpg")):
        text, confidence = _pick_best_ocr(frame_path)
        if confidence < min_confidence:
            continue

        cleaned = _clean_ocr(text)
        if not cleaned or len(cleaned) < 5 or cleaned == previous_text:
            continue

        previous_text = cleaned
        match = re.search(r"(\d+)", frame_path.stem)
        seconds = float(match.group(1)) if match else 0.0
        segments.append(
            {
                "start": seconds,
                "end": seconds + 1.0,
                "text": cleaned,
                "source": "ocr",
                "confidence": round(confidence, 1),
            }
        )

    write_json(ocr_path, segments)
    return segments


def align_segments(asr_segments: list[dict], ocr_segments: list[dict]) -> list[dict]:
    merged = list(asr_segments) + list(ocr_segments)
    merged.sort(key=lambda item: item["start"])
    return merged


def run(audio_path: str | Path, frames_dir: str | Path, model_size: str = "small") -> dict:
    audio = Path(audio_path)
    frames = Path(frames_dir)
    out_dir = audio.parent

    asr_segments, language_payload = run_asr(audio, model_size=model_size)
    ocr_segments = run_ocr(frames)
    aligned_segments = align_segments(asr_segments, ocr_segments)

    aligned_path = out_dir / "aligned_segments.json"
    write_json(aligned_path, aligned_segments)

    return {
        "aligned_path": str(aligned_path),
        "n_asr_segments": len(asr_segments),
        "n_ocr_segments": len(ocr_segments),
        "n_aligned": len(aligned_segments),
        "detected_language": language_payload["language"],
    }

