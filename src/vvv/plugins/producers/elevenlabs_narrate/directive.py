from __future__ import annotations
import re
from typing import Any

from vvv.registry import register_directive
from vvv.interfaces.directive import Directive
from .node import NarrateNode


_VOICE_ID = re.compile(
    r"""
    \s*
    \[                                      # opening bracket
    voice:
    .*                                      # group 1: voice_id
    \]                                      # closing bracket
    $
    """,
    re.VERBOSE,
)


def _parse_narrate(value: Any, entry: dict, matched_key: str) -> NarrateNode:
    text = str(value)
    voice_id = entry.get("voice")
    return NarrateNode(text=text, voice=voice_id)


register_directive(Directive("narrate", ("n", "narrate"), _parse_narrate))
