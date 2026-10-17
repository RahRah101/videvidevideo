"""Wires concrete producers, sync provider, and assembler into the pipeline."""
from __future__ import annotations

from vvv.plugins.producers.elevenlabs_narrate.node import NarrateNode
from vvv.plugins.producers.clip.node import ClipNode
from vvv.plugins.producers.pause.node import PauseNode
from vvv.plugins.producers.stems.node import StemNode
from vvv.plugins.producers.title.node import TitleNode
from vvv.interfaces.producer import Producer
from vvv.interfaces.sync import SyncProvider
from vvv.interfaces.assembler import Assembler
from vvv.config import Config

from vvv.plugins.producers.pause.producer import PauseProducer
from vvv.plugins.producers.elevenlabs_narrate.producer import NarrateProducer
from vvv.plugins.producers.elevenlabs_narrate.elevenlabs_impl import ElevenLabsTTS
#from vvv.plugins.producers.elevenlabs_narrate.mock_tts import MockTTS
from vvv.plugins.producers.clip.producer import ClipProducer
from vvv.plugins.assemblers.kdencli.assembler import KdencliAssembler
from vvv.phases.sync import SequentialSync

from vvv.plugins.producers.stems.stem_backend import get_backend
from vvv.plugins.producers.stems import StemProducer
import os

from vvv.plugins.producers.title.producer import TitleProducer

def build_producers(config: Config | None = None) -> dict[type, Producer]:
    # Components read their own config section (from_config); this file never learns their keys.
    # TODO: Replace with config file later... (stem backend still env-var)
    config = config or Config()
    stem_backend = get_backend(os.environ.get("VVV_STEM_BACKEND", "demucs"))
    return {
        PauseNode: PauseProducer(),
        # TODO: Config config config. For now we forcing eleven labs because we trying to test a working product
        # but this should be configurable
        NarrateNode: NarrateProducer.from_config(config, tts=ElevenLabsTTS.from_config(config)),
        ClipNode: ClipProducer(),
        StemNode:    StemProducer(stem_backend),
        TitleNode: TitleProducer(),
    }


def build_sync() -> SyncProvider:
    return SequentialSync()


def build_assembler() -> Assembler:
    return KdencliAssembler()
