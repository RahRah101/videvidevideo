from __future__ import annotations
import re
import urllib.parse
from pathlib import Path

from vvv.registry import register_source
from vvv.interfaces.source import SourceHandler, SourceInfo
from vvv.context import Context
from vvv.util.media import download_video_media


# Youtube h/m/s tokens
_HMS_TOKEN = re.compile(
    r"""
    (?:(\d+)h)?     # hours
    (?:(\d+)m)?     # minutes
    (?:(\d+)s)?     # seconds
    """,
    re.VERBOSE,
)


class YouTubeHandler(SourceHandler):
    def handles(self, source: str) -> bool:
        return "youtube.com" in source or "youtu.be" or "instagram" in source

    def resolve(self, source: str, ctx: Context) -> SourceInfo:
        download_dir = ctx.work_dir / "media"
        # TODO: Sometimes the user gives start/end hints 
        # and downloading the full video is a waste of time and data
        # When yt-dlp can use --download-sections
        # Problem is that this kinda fck up the separation of concerns 
        # Because the downloader is not *supposed* to handle *trimming*.
        # Trimming is normally an Assembler concern, not a SourceHandler concern
        # (or is it??? Editorial trim =/= acquisition trim ???).
        # It's "cleaner" to download the whole thing and then trim it. 
        # But also more wasteful. 
        path = download_video_media(source, download_dir)
        return SourceInfo(
            path=Path(path),
            meta={"start_hint": self._start_hint(source)},
        )

    def _start_hint(self, url: str) -> float | None:
        params = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
        for key in ("t", "start"):
            if key in params and params[key]:
                return _parse_time_token(params[key][0])
        return None


def _parse_time_token(token: str) -> float:
    token = token.strip()
    if token.isdigit():# bare num, e.g. ?t=93
        return float(token)

    m = _HMS_TOKEN.fullmatch(token)
    if m and any(m.groups()):
        h, mins, s = (int(g or 0) for g in m.groups())
        return float(h * 3600 + mins * 60 + s)

    raise ValueError(f"unparseable time token: {token!r}")

register_source(YouTubeHandler())