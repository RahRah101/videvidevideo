from __future__ import annotations
from typing import Any

from vvv.registry import register_directive
from vvv.interfaces.directive import Directive
from .node import TitleNode, TitleStyle


def _parse_title(value: Any, entry: dict, matched_key: str) -> TitleNode:
    style = _parse_style(entry.get("style", {}))
    return TitleNode(
        text=str(value),
        anchor=entry.get("anchor", "bottom-center"),
        margin=int(entry.get("margin", 80)),
        x=entry.get("x"),
        y=entry.get("y"),
        track=entry.get("track"),
        duration_s=float(entry.get("duration", 5.0)),
        style=style,
    )

def _parse_style(raw: dict) -> TitleStyle:
    return TitleStyle(
        font=raw.get("font", "Arial"),
        font_size=int(raw.get("font_size", raw.get("size", 50))),
        color=raw.get("color", "255,255,255,255"),
        outline_color=raw.get("outline_color", "0,0,0,255"),
        outline=str(raw.get("outline", "2")),
        bold=bool(raw.get("bold", False)),
        italic=bool(raw.get("italic", False)),
        underline=bool(raw.get("underline", False)),
        letter_spacing=int(raw.get("letter_spacing", 0)),
        line_spacing=int(raw.get("line_spacing", 0)),
        box_width=int(raw.get("box_width", 0)),
        box_height=int(raw.get("box_height", 0)),
        font_file=raw.get("font_file"),
        shadow=raw.get("shadow"),
        gradient=raw.get("gradient"),
    )


register_directive(Directive("title", ("title", "text"), _parse_title))
