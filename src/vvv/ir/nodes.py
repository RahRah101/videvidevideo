from __future__ import annotations


class Node:
    """Base of every directive's IR node.

    Concrete nodes are frozen dataclasses that live in their directive's plugin
    package (e.g. plugins/producers/clip/node.py), not here. Core only knows this base.
    """
    __slots__ = ()
