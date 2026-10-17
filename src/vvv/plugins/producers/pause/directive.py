from __future__ import annotations
from typing import Any

from vvv.registry import register_directive
from vvv.interfaces.directive import Directive
from .node import PauseNode


def _parse_pause(value: Any, entry: dict, matched_key: str) -> PauseNode:
    return PauseNode(duration_s=float(value))


register_directive(Directive("pause", ("_", "pause"), _parse_pause))
