from __future__ import annotations

from abc import ABC, abstractmethod

from litassist.models import Paper


class SearchError(RuntimeError):
    pass


class Searcher(ABC):
    source: str

    @abstractmethod
    def search(self, query: str, limit: int) -> list[Paper]:
        raise NotImplementedError
