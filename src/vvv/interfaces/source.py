from __future__ import annotations
from abc import ABC, abstractmethod
from typing import ClassVar
from dataclasses import dataclass, field
from pathlib import Path

from vvv.context import Context

@dataclass(frozen=True, slots=True)
class SourceInfo:
    path: Path
    #This carries info carried from the source.
    #This isn't just metadata in the usual "written into file" sense
    #For example if the soure is a youtube link, the 
    #Link itself could have a start time to extract
    #Also the creator, time uploaded, etc... things you might not
    #find in the file's metadata but that come from the source
    meta: dict = field(default_factory=dict)
    
class SourceHandler(ABC):
    # resolve_media asks handlers in ascending priority; the first that handles() wins.
    # Catch-alls (e.g. every URL -> yt-dlp) use a high number so specific handlers go first.
    priority: ClassVar[int] = 50

    @abstractmethod
    def handles(self, source: str) -> bool: 
        ...
    @abstractmethod
    def resolve(self, source: str, ctx: Context) -> SourceInfo: 
        ...

