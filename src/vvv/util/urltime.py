from __future__ import annotations
import re
import urllib.parse


def parse_youtube_start(url: str) -> float | None:
    query = urllib.parse.urlparse(url).query
    params = urllib.parse.parse_qs(query)

    raw = None
    for key in ("t", "start"):
        if key in params and params[key]:
            raw = params[key][0]
            break
    if raw is None:
        return None

    return _parse_time_token(raw)


def _parse_time_token(token: str) -> float:
    """'93' -> 93, '93s' -> 93, '1m33s' -> 93, '1h2m3s' -> 3723."""
    token = token.strip()
    if token.isdigit():
        return float(token)

    m = re.fullmatch(
        r"(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?",
        token,
    )
    if not m or not any(m.groups()):
        if token.endswith("s") and token[:-1].isdigit():
            return float(token[:-1])
        raise ValueError(f"unparseable time token: {token!r}")

    h = int(m.group(1) or 0)
    mins = int(m.group(2) or 0)
    s = int(m.group(3) or 0)
    return float(h * 3600 + mins * 60 + s)
