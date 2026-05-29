"""Text helpers for concept names and transcript snippets."""

from __future__ import annotations

import re


def slugify(value: str) -> str:
    lowered = humanize_concept(value).lower()
    lowered = re.sub(r"[^a-z0-9]+", "-", lowered).strip("-")
    return lowered or "concept"


def humanize_concept(value: str) -> str:
    text = value.replace("_", " ").replace("-", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def titleize_concept(value: str) -> str:
    words = humanize_concept(value).split()
    keep_upper = {"bfs", "dfs", "sql", "dbms", "ocr", "asr", "llm"}
    rendered = []
    for word in words:
        if word.lower() in keep_upper:
            rendered.append(word.upper())
        elif len(word) == 1 and word.isalpha():
            rendered.append(word.upper())
        else:
            rendered.append(word.capitalize())
    return " ".join(rendered)


def concept_variants(value: str) -> set[str]:
    base = humanize_concept(value).lower()
    variants = {
        base,
        base.replace("-", " "),
        base.replace(" ", ""),
        base.replace(" ", "_"),
        base.replace(" ", "-"),
    }
    return {variant for variant in variants if variant}


def compact_snippet(text: str, max_length: int = 180) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip()
    if len(cleaned) <= max_length:
        return cleaned
    return cleaned[: max_length - 3].rstrip() + "..."

