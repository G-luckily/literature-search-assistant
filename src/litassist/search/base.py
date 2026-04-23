from __future__ import annotations

from abc import ABC, abstractmethod

from litassist.models import Paper


class SearchError(RuntimeError):
    def __init__(self, message: str, meta: dict | None = None):
        super().__init__(message)
        self.meta = meta or {}


class Searcher(ABC):
    source: str

    @abstractmethod
    def search(self, query: str, limit: int) -> list[Paper]:
        raise NotImplementedError
