from __future__ import annotations

import json
import os
import tomllib
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class GeneralConfig:
    contact_email: str = ""
    user_agent: str = "literature-search-assistant/0.1"
    request_timeout_seconds: float = 20
    max_results_per_source: int = 20
    from_year: int | None = field(default_factory=lambda: date.today().year - 4)
    prefer_recent: bool = True
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
class GoogleScholarConfig:
    api_key: str = ""
    endpoint: str = "https://serpapi.com/search.json"


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
    google_scholar: GoogleScholarConfig = field(default_factory=GoogleScholarConfig)
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
    google_scholar = GoogleScholarConfig(**data.get("google_scholar", {}))
    llm_data = data.get("llm", {})
    llm = LLMConfig(**llm_data)
    zotero = ZoteroConfig(**data.get("zotero", {}))

    general.contact_email = os.getenv("LITASSIST_CONTACT_EMAIL", general.contact_email)
    if os.getenv("LITASSIST_FROM_YEAR"):
        general.from_year = int(os.getenv("LITASSIST_FROM_YEAR", "0")) or None
    if os.getenv("LITASSIST_PREFER_RECENT"):
        general.prefer_recent = _env_bool("LITASSIST_PREFER_RECENT")
    zotero.library_id = os.getenv("ZOTERO_LIBRARY_ID", zotero.library_id)
    zotero.library_type = os.getenv("ZOTERO_LIBRARY_TYPE", zotero.library_type)
    zotero.api_key = os.getenv("ZOTERO_API_KEY", zotero.api_key)
    zotero.collection_key = os.getenv("ZOTERO_COLLECTION_KEY", zotero.collection_key)
    semantic_scholar.api_key = os.getenv(
        "SEMANTIC_SCHOLAR_API_KEY", semantic_scholar.api_key
    )
    web_of_science.api_key = os.getenv("WOS_API_KEY", web_of_science.api_key)
    google_scholar.api_key = os.getenv(
        "SERPAPI_API_KEY",
        os.getenv("GOOGLE_SCHOLAR_SERPAPI_KEY", google_scholar.api_key),
    )
    google_scholar.endpoint = os.getenv(
        "GOOGLE_SCHOLAR_SERPAPI_ENDPOINT",
        google_scholar.endpoint,
    )
    llm.provider = os.getenv("LITASSIST_LLM_PROVIDER", llm.provider).strip().lower()
    if llm.provider == "deepseek":
        if "model" not in llm_data and not os.getenv("DEEPSEEK_MODEL"):
            llm.model = "deepseek-chat"
        if "endpoint" not in llm_data and not os.getenv("DEEPSEEK_BASE_URL"):
            llm.endpoint = "https://api.deepseek.com/v1"
        llm.api_key = os.getenv("DEEPSEEK_API_KEY", llm.api_key)
        llm.model = os.getenv("DEEPSEEK_MODEL", llm.model)
        llm.endpoint = os.getenv("DEEPSEEK_BASE_URL", llm.endpoint)
    else:
        llm.api_key = os.getenv("OPENAI_API_KEY", llm.api_key)
        llm.model = os.getenv("OPENAI_MODEL", llm.model)
        llm.endpoint = os.getenv("OPENAI_RESPONSES_ENDPOINT", llm.endpoint)
    llm.api_key = os.getenv("LITASSIST_LLM_API_KEY", llm.api_key)
    llm.model = os.getenv("LITASSIST_LLM_MODEL", llm.model)
    llm.endpoint = os.getenv("LITASSIST_LLM_ENDPOINT", llm.endpoint)
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
        google_scholar=google_scholar,
        llm=llm,
        zotero=zotero,
    )


def save_llm_config(
    path: str | Path,
    values: dict[str, Any],
    preserve_empty_api_key: bool = True,
) -> AppConfig:
    config_path = Path(path)
    data: dict[str, Any] = {}
    if config_path.exists():
        data = tomllib.loads(config_path.read_text(encoding="utf-8"))

    llm = dict(data.get("llm", {}))
    for key in ("enabled", "provider", "model", "endpoint", "request_timeout_seconds"):
        if key in values and values[key] is not None:
            llm[key] = values[key]

    if "api_key" in values:
        api_key = values["api_key"]
        if api_key or not preserve_empty_api_key:
            llm["api_key"] = api_key

    data["llm"] = llm
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(_dump_toml(data), encoding="utf-8")
    return load_config(config_path)


def save_source_config(path: str | Path, values: dict[str, Any]) -> AppConfig:
    config_path = Path(path)
    data: dict[str, Any] = {}
    if config_path.exists():
        data = tomllib.loads(config_path.read_text(encoding="utf-8"))

    general = dict(data.get("general", {}))
    if "from_year" in values:
        if values["from_year"] is None:
            general.pop("from_year", None)
        else:
            general["from_year"] = values["from_year"]
    if "prefer_recent" in values:
        general["prefer_recent"] = values["prefer_recent"]
    data["general"] = general

    for section in ("semantic_scholar", "web_of_science", "google_scholar"):
        if section not in values:
            continue
        current = dict(data.get(section, {}))
        for key, value in values[section].items():
            if value is not None:
                current[key] = value
        data[section] = current

    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(_dump_toml(data), encoding="utf-8")
    return load_config(config_path)


def _dump_toml(data: dict[str, Any]) -> str:
    lines: list[str] = []
    root_items = {
        key: value for key, value in data.items() if not isinstance(value, dict)
    }
    if root_items:
        _append_toml_values(lines, root_items)

    for section, values in data.items():
        if not isinstance(values, dict):
            continue
        if lines:
            lines.append("")
        lines.append(f"[{section}]")
        _append_toml_values(lines, values)

    return "\n".join(lines).rstrip() + "\n"


def _append_toml_values(lines: list[str], values: dict[str, Any]) -> None:
    for key, value in values.items():
        lines.append(f"{key} = {_toml_value(value)}")


def _toml_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int | float):
        return str(value)
    if isinstance(value, list):
        return "[" + ", ".join(_toml_value(item) for item in value) + "]"
    return json.dumps(str(value), ensure_ascii=False)


def _env_bool(name: str) -> bool:
    return os.getenv(name, "").lower() in {"1", "true", "yes", "on"}
