# Source Integration Strategy

## Priority Order

1. Official APIs and open scholarly APIs.
2. Citation export endpoints such as RIS, BibTeX, EndNote, RefWorks.
3. Zotero translators through Zotero Translation Server.
4. User-mediated browser workflows.
5. Page scraping only for low-frequency metadata fallback.

The project should not implement bypasses for paywalls, CAPTCHA, access controls, or institutional download limits.

## Query Planning

The planner has two modes:

- Rule mode: deterministic bilingual keyword extraction, always available offline.
- LLM mode: optional structured research-question decomposition using an OpenAI API key.

LLM mode should produce research questions, concept groups, inclusion/exclusion criteria, and source-specific search strings. It must remain optional so the search pipeline is still usable without external model credentials.

## Zotero

Use Zotero as the final library of record.

- Use `pyzotero` or Zotero Web API for creating items and adding tags/collections.
- Use Zotero Translation Server to convert article pages into Zotero API JSON when a translator exists.
- Keep source metadata in tags and `extra`: search source, query, imported date, PDF URL, and external IDs.
- Do not write directly to Zotero's local SQLite database.

Open-source references:

- `zotero/translators`
- `zotero/translation-server`
- `urschrei/pyzotero`

## Web of Science

Use official Clarivate APIs.

- Starter API can support basic document search and metadata retrieval.
- Expanded API is better for richer metadata, cited references, and citing items.
- Require user-provided API key and respect plan limits.
- Preserve the exact WoS advanced query string in every run report.

Open-source references:

- `clarivate/wosstarter_python_client`
- `clarivate/wosstarter-javascript-client`

## CNKI

CNKI should be implemented as a conservative, user-authorized workflow.

Recommended path:

1. Let the user search or log in through the browser when institutional access is needed.
2. Prefer CNKI citation export data over raw DOM scraping.
3. Parse EndNote / RefWorks / RIS-style exports into normalized paper records.
4. Use Zotero translators from the Chinese community when possible.
5. Attach locally downloaded files by title/DOI similarity only after the user has obtained them legally.

Do not build unattended bulk full-text download as a core feature.

Open-source references:

- `l0o0/translators_CN`
- `l0o0/jasminum`
- `h-lu/cnki-mcp`

## Google Scholar

Google Scholar is useful for discovery and cross-checking, but it should not be the default automated source.

Recommended path:

- Use it as an optional browser-assisted source.
- Keep request volume low.
- Prefer saving individual result pages through Zotero Connector / Translation Server.
- Use OpenAlex, Crossref, Semantic Scholar, and Web of Science as primary machine-readable sources.

Open-source references:

- `scholarly-python-package/scholarly`

## OpenAlex / Crossref / Semantic Scholar

These are the MVP's default sources.

- OpenAlex: broad discovery, DOI, open access status, PDF URLs, citation counts.
- Crossref: DOI and publication metadata validation.
- Semantic Scholar: abstracts, citations, open PDF hints, related graph features.

Semantic Scholar anonymous shared limits can return `429`; configure `SEMANTIC_SCHOLAR_API_KEY` for more stable access.

## Open Access Full Text

Use DOI-based open access enrichment before attempting any platform-specific download.

- Prefer Unpaywall/OpenAlex open access locations.
- Keep publisher landing pages even when no PDF is found.
- Discard URLs that are clearly images or non-PDF assets before presenting them as PDF links.
- Treat full-text download as optional and only for open access or user-authorized institutional access.
