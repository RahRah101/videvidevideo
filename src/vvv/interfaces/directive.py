from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Callable

from vvv.ir.nodes import Node


@dataclass(frozen=True, slots=True)
class Directive:
    """One DSL directive: which entry keys trigger it and how to turn the entry into a Node.

    parse(value, entry, matched_key) -> Node
      value       = entry[matched_key]
      entry       = the whole YAML entry (for entry-level keys like from:/to:)
      matched_key = the alias that matched (e.g. "i" vs "v")
    """
    name: str
    aliases: tuple[str, ...]
    parse: Callable[[Any, dict, str], Node]
