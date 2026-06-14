
from __future__ import annotations
from pathlib import Path

from vvv.interfaces.producer import Producer
from vvv.ir.nodes import StemNode
from vvv.ir.resolved import ResolvedEntry
from vvv.context import Context
from vvv.util.media import resolve_media, probe_duration, trim
from .stem_backend import StemSeparator


class StemProducer(Producer):
    node_type = StemNode

    def __init__(self, separator: StemSeparator):
        self.separator = separator

    def produce(self, node: StemNode, ctx: Context) -> ResolvedEntry:
        info = resolve_media(node.source, ctx)
        audio = info.path

        # processing trim: isolate the segment BEFORE separating, so we only
        # process/upload what we need (saves time + tokens).
        audio = trim(audio, node.from_s, node.to_s, ctx.work_dir / "stems")

        stem_paths = self.separator.separate(audio, list(node.stems), ctx.work_dir / "stems")

        chosen = node.stems[0]
        media = stem_paths[chosen]
        return ResolvedEntry(
            node=node,
            media=media,
            kind="audio",
            duration_s=probe_duration(media),
            extras={"stem": chosen, "source": node.source},
        )