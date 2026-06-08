from __future__ import annotations
import re

# Filename slug: lowercase, keep [a-z0-9_-], turn everything else to _
_SLUG_FORBIDDEN = re.compile(r"[^\w\-]+")


def slugify(text: str, max_len: int = 50, fallback: str = "project") -> str:
    """Turn arbitrary text into a safe filename stem.
    """
    slug = _SLUG_FORBIDDEN.sub("_", text.lower()).strip("_")[:max_len]
    return slug or fallback