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
      matched_key = the alias that matched (e.g. "title" vs "t")
      Raise ValueError on bad input; parse collects every error in the script and reports them together.

    keys = entry-level keys this directive reads besides its alias. parse warns on keys no
    directive in the entry claims, and errors when two directives in one entry claim the same key.
    """
    name: str
    aliases: tuple[str, ...]
    parse: Callable[[Any, dict, str], Node]
    keys: frozenset[str] = frozenset()
