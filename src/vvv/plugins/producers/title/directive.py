from __future__ import annotations
from dataclasses import fields
from typing import Any

from vvv.registry import register_directive
from vvv.interfaces.directive import Directive
from vvv.util.dsl import pick
from .node import TitleNode, TitleStyle


_STYLE_KEYS = {f.name for f in fields(TitleStyle)} | {"size"}   # size = alias of font_size


def _parse_title(value: Any, entry: dict, matched_key: str) -> TitleNode:
    style = _parse_style(entry.get("style", {}))
    return TitleNode(
        text=str(value),
        anchor=entry.get("anchor", "bottom-center"),
        margin=int(entry.get("margin", 80)),
        x=entry.get("x"),
        y=entry.get("y"),
        track=entry.get("track"),
        duration_s=float(pick(entry, "duration", "d", default=5.0)),
        style=style,
    )

def _parse_style(raw: dict) -> TitleStyle:
    if not isinstance(raw, dict):
        raise ValueError(f"style: must be a mapping, got {raw!r}")
    unknown = sorted(set(raw) - _STYLE_KEYS)
    if unknown:
        raise ValueError(f"unknown style key(s) {unknown}; known: {sorted(_STYLE_KEYS)}")
    return TitleStyle(
        font=raw.get("font", "Arial"),
        font_size=int(pick(raw, "font_size", "size", default=50)),
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


register_directive(Directive(
    "title", ("t", "title", "text"), _parse_title,
    frozenset({"style", "anchor", "margin", "x", "y", "track", "duration", "d"}),
))
