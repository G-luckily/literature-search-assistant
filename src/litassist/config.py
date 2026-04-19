from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class GeneralConfig:
    contact_email: str = ""
    user_agent: str = "literature-search-assistant/0.1"
    request_timeout_seconds: float = 20
    max_results_per_source: int = 20
    enabled_sources: list[str] = field(
        default_factory=lambda: ["openalex", "crossref", "semantic_scholar"]
    )


@dataclass(slots=True)
class SemanticScholarConfig:
    api_key: str = ""


@dataclass(slots=True)
class WebOfScienceConfig:
    api_key: str = ""
    endpoint: str = "https://api.clarivate.com/apis/wos-starter/v1/documents"


@dataclass(slots=True)
class LLMConfig:
    provider: str = "openai"
    enabled: bool = False
    api_key: str = ""
    model: str = "gpt-4.1-mini"
    endpoint: str = "https://api.openai.com/v1/responses"
    request_timeout_seconds: float = 45


@dataclass(slots=True)
class ZoteroConfig:
    library_id: str = ""
    library_type: str = "user"
    api_key: str = ""
    collection_key: str = ""


@dataclass(slots=True)
class AppConfig:
    general: GeneralConfig = field(default_factory=GeneralConfig)
    semantic_scholar: SemanticScholarConfig = field(default_factory=SemanticScholarConfig)
    web_of_science: WebOfScienceConfig = field(default_factory=WebOfScienceConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    zotero: ZoteroConfig = field(default_factory=ZoteroConfig)


def load_config(path: str | Path | None = None) -> AppConfig:
    data = {}
    if path:
        config_path = Path(path)
        if config_path.exists():
            data = tomllib.loads(config_path.read_text(encoding="utf-8"))
    elif Path("config.toml").exists():
        data = tomllib.loads(Path("config.toml").read_text(encoding="utf-8"))

    general = GeneralConfig(**data.get("general", {}))
    semantic_scholar = SemanticScholarConfig(**data.get("semantic_scholar", {}))
    web_of_science = WebOfScienceConfig(**data.get("web_of_science", {}))
    llm = LLMConfig(**data.get("llm", {}))
    zotero = ZoteroConfig(**data.get("zotero", {}))

    general.contact_email = os.getenv("LITASSIST_CONTACT_EMAIL", general.contact_email)
    zotero.library_id = os.getenv("ZOTERO_LIBRARY_ID", zotero.library_id)
    zotero.library_type = os.getenv("ZOTERO_LIBRARY_TYPE", zotero.library_type)
    zotero.api_key = os.getenv("ZOTERO_API_KEY", zotero.api_key)
    zotero.collection_key = os.getenv("ZOTERO_COLLECTION_KEY", zotero.collection_key)
    semantic_scholar.api_key = os.getenv(
        "SEMANTIC_SCHOLAR_API_KEY", semantic_scholar.api_key
    )
    web_of_science.api_key = os.getenv("WOS_API_KEY", web_of_science.api_key)
    llm.api_key = os.getenv("OPENAI_API_KEY", llm.api_key)
    llm.model = os.getenv("OPENAI_MODEL", llm.model)
    if os.getenv("LITASSIST_LLM_ENABLED"):
        llm.enabled = os.getenv("LITASSIST_LLM_ENABLED", "").lower() in {
            "1",
            "true",
            "yes",
            "on",
        }

    return AppConfig(
        general=general,
        semantic_scholar=semantic_scholar,
        web_of_science=web_of_science,
        llm=llm,
        zotero=zotero,
    )
