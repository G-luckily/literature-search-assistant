from __future__ import annotations

import argparse
import json
from pathlib import Path

from .config import load_config
from .pipeline import _build_search_plan, run_search
from .report import load_papers, write_json, write_run
from .web import find_free_port, serve
from .zotero import import_papers


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="litassist",
        description="Literature search assistant with Zotero integration.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    plan_parser = subparsers.add_parser("plan", help="Build a search plan.")
    plan_parser.add_argument("need")
    plan_parser.add_argument("--config", default=None)
    plan_parser.add_argument("--llm", action="store_true", help="Use LLM planning.")
    _add_keyword_args(plan_parser)
    plan_parser.add_argument("--out", help="Optional JSON output path.")

    search_parser = subparsers.add_parser("search", help="Run multi-source search.")
    search_parser.add_argument("need")
    search_parser.add_argument("--config", default=None)
    search_parser.add_argument("--out", default="runs/latest")
    search_parser.add_argument("--limit", type=int, default=None)
    search_parser.add_argument("--llm", action="store_true", help="Use LLM planning.")
    search_parser.add_argument(
        "--source",
        action="append",
        choices=["openalex", "crossref", "semantic_scholar", "web_of_science"],
        help="Source to query. Can be repeated.",
    )
    _add_keyword_args(search_parser)

    import_parser = subparsers.add_parser(
        "import-zotero", help="Import a papers.json file into Zotero."
    )
    import_parser.add_argument("papers_json")
    import_parser.add_argument("--config", default=None)
    import_parser.add_argument("--limit", type=int, default=None)
    import_parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually write to Zotero. Without this flag the command is a dry run.",
    )

    web_parser = subparsers.add_parser("web", help="Start the local web interface.")
    web_parser.add_argument("--config", default=None)
    web_parser.add_argument("--host", default="127.0.0.1")
    web_parser.add_argument("--port", type=int, default=8765)

    args = parser.parse_args(argv)

    if args.command == "plan":
        config = load_config(args.config)
        plan = _build_search_plan(
            args.need,
            config=config,
            zh_keywords=args.zh_keyword,
            en_keywords=args.en_keyword,
            use_llm=args.llm,
        )
        payload = plan.to_dict()
        if args.out:
            write_json(args.out, payload)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    if args.command == "search":
        config = load_config(args.config)
        run = run_search(
            args.need,
            config=config,
            sources=args.source,
            limit=args.limit,
            zh_keywords=args.zh_keyword,
            en_keywords=args.en_keyword,
            use_llm=args.llm,
        )
        write_run(run, args.out)
        print(f"Wrote {len(run.papers)} deduped papers to {Path(args.out).resolve()}")
        if run.errors:
            print("Source errors:")
            for source, error in run.errors.items():
                print(f"- {source}: {error}")
        return

    if args.command == "import-zotero":
        config = load_config(args.config)
        papers = load_papers(args.papers_json)
        result = import_papers(
            papers,
            config.zotero,
            limit=args.limit,
            apply=args.apply,
        )
        print(
            f"Zotero import result: created={result.created}, skipped={result.skipped}, errors={len(result.errors)}"
        )
        for error in result.errors:
            print(f"- {error}")
        return

    if args.command == "web":
        port = find_free_port(args.host, args.port)
        serve(host=args.host, port=port, config_path=args.config)
        return


def _add_keyword_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--zh-keyword",
        action="append",
        default=None,
        help="Chinese keyword override/addition. Can be repeated.",
    )
    parser.add_argument(
        "--en-keyword",
        action="append",
        default=None,
        help="English keyword override/addition. Can be repeated.",
    )
