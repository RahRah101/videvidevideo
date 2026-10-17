from __future__ import annotations
import re

# Shared by directives that take a source with an optional inline range: "clip.mp4 [1:01-1:06]"
TIMESTAMP_RANGE = re.compile(
    r"""
    \s*
    \[                                      # opening bracket
    (\d{1,2}(?::\d{2}){1,2}(?:\.\d+)?)      # group 1: start, M:SS or H:MM:SS, optional .fraction
    -                                       # separator (":")
    (\d{1,2}(?::\d{2}){1,2}(?:\.\d+)?)      # group 2: end, same
    \]                                      # closing bracket
    $
    """,
    re.VERBOSE,
)


def parse_timestamp(ts: str) -> float:
    # '1:05' -> 65.0, '1:02:03' -> 3723.0, '12' -> 12.0, '1:05.5' -> 65.5
    *whole, last = str(ts).strip().split(":")
    seconds = 0
    for p in whole:
        seconds = seconds * 60 + int(p)
    return float(seconds * 60 + float(last)) if whole else float(last)
