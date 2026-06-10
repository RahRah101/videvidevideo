from pathlib import Path
from vvv.ir.nodes import NarrateNode
from vvv.context import Context, Meta
from vvv.plugins.producers.elevenlabs_narrate.producer import NarrateProducer
from vvv.plugins.producers.elevenlabs_narrate.elevenlabs_impl import ElevenLabsTTS
import os

ctx = Context(
    meta=Meta(
        title="test",
        voice_id=os.environ["ELEVENLABS_VOICE_ID"], 
        fps=30,
        resolution=(1920, 1080),
        assets_dir=Path("assets"),
        char_lim=5000,
    ),
    work_dir=Path("build"),
)

p = NarrateProducer(tts=ElevenLabsTTS())
result = p.produce(
    NarrateNode(text="Testing the new architecture. Beat drops in three two one."),
    ctx,
)
print(result)
assert result.media is not None
print(f"file exists: {result.media.exists()}, size: {result.media.stat().st_size} bytes")
