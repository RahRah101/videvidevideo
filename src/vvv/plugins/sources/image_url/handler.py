from __future__ import annotations
import re
import urllib.parse
from pathlib import Path

from vvv.registry import register_source
from vvv.interfaces.source import SourceHandler, SourceInfo
from vvv.context import Context
from vvv.util.media import download_image_media, is_url, is_image

class ImageHandler(SourceHandler):
    def handles(self, source: str) -> bool:
        return is_url(source) and bool(is_image(source))

    def resolve(self, source: str, ctx: Context) -> SourceInfo:
        download_dir = ctx.work_dir / "media"
        path = download_image_media(source, download_dir)
        return SourceInfo(
            path=Path(path)
        )

register_source(ImageHandler())