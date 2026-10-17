
from __future__ import annotations
import os
from pathlib import Path

from vvv.registry import register_producer
from vvv.interfaces.producer import Producer
from .node import StemNode
from vvv.ir.resolved import ResolvedEntry
from vvv.context import Context
from vvv.util.media import resolve_media, probe_duration, trim
from .stem_backend import StemSeparator, available_backends, get_backend_class


@register_producer
class StemProducer(Producer):
    node_type = StemNode
    CONFIG_SECTION = "stem"
    CONFIG_KEYS = {"backend"}

    @classmethod
    def build(cls, config) -> "StemProducer":
        # backend: script config > $VVV_STEM_BACKEND > demucs
        section = config.section(cls.CONFIG_SECTION, cls.CONFIG_KEYS)
        name = section.get("backend") or os.environ.get("VVV_STEM_BACKEND") or "demucs"
        return cls(get_backend_class(str(name)).from_config(config))

    @classmethod
    def config_sections(cls) -> set[str]:
        # each backend reads a section named after its entry point
        return {cls.CONFIG_SECTION, *available_backends()}

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