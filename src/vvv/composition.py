"""Wires concrete producers, sync provider, and assembler into the pipeline."""
from __future__ import annotations

from vvv.ir.nodes import NarrateNode, ClipNode, PauseNode, StemNode, TitleNode
from vvv.interfaces.producer import Producer
from vvv.interfaces.sync import SyncProvider
from vvv.interfaces.assembler import Assembler

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

def build_producers() -> dict[type, Producer]:
    # TODO: Replace with config file later...
    stem_backend = get_backend(os.environ.get("VVV_STEM_BACKEND", "demucs"))
    return {
        PauseNode: PauseProducer(),
        # TODO: Config config config. For now we forcing eleven labs because we trying to test a working product
        # but this should be configurable
        NarrateNode: NarrateProducer(tts=ElevenLabsTTS()),
        ClipNode: ClipProducer(),
        StemNode:    StemProducer(stem_backend),
        TitleNode: TitleProducer(),
    }


def build_sync() -> SyncProvider:
    return SequentialSync()


def build_assembler() -> Assembler:
    return KdencliAssembler()
