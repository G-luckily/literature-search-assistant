from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class ResearchPlan:
    need: str
    zh_keywords: list[str]
    en_keywords: list[str]
    queries: dict[str, str]
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class Paper:
    title: str
    source: str
    authors: list[str] = field(default_factory=list)
    year: int | None = None
    venue: str | None = None
    abstract: str | None = None
    doi: str | None = None
    url: str | None = None
    pdf_url: str | None = None
    external_id: str | None = None
    cited_by_count: int | None = None
    score: float | None = None
    sources: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        if not self.sources:
            self.sources = [self.source]

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        if not data["raw"]:
            data.pop("raw")
        return data
