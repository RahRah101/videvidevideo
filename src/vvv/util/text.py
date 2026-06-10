from __future__ import annotations
import re

# Filename slug: lowercase, keep [a-z0-9_-], turn everything else to _
_SLUG_FORBIDDEN = re.compile(r"[^\w\-]+")

# A sentence ends with a ., ?, or !
_SENTENCE_END = re.compile(r'(?<=[.!?])\s+')


def slugify(text: str, max_len: int = 50, fallback: str = "project") -> str:
    """Turn arbitrary text into a safe filename stem.
    """
    slug = _SLUG_FORBIDDEN.sub("_", text.lower()).strip("_")[:max_len]
    return slug or fallback


def split_for_tts(text: str, char_lim: int = 5000) -> list[str]:
    """Split text into chunks each <= char_lim"""
    text = text.strip()
    if not text:
        return []
    if len(text) <= char_lim:
        return [text]

    sentences = _SENTENCE_END.split(text)
    chunks: list[str] = []
    current = ""

    for sentence in sentences:
        if len(sentence) > char_lim:
            if current:
                chunks.append(current)
                current = ""
            chunks.extend(_hard_split(sentence, char_lim))
            continue

        candidate = sentence if not current else current + " " + sentence
        if len(candidate) <= char_lim:
            current = candidate
        else:
            chunks.append(current)
            current = sentence

    if current:
        chunks.append(current)
    return chunks


def _hard_split(text: str, char_lim: int) -> list[str]:
    """Split on whitespace when a single sentence is too long."""
    words = text.split()
    chunks: list[str] = []
    current = ""
    for word in words:
        candidate = word if not current else current + " " + word
        if len(candidate) <= char_lim:
            current = candidate
        else:
            if current:
                chunks.append(current)
            current = word
    if current:
        chunks.append(current)
    return chunks