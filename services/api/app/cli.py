"""Operational commands (plan §15.4).

python -m app.cli migrate          apply database migrations (explicit; never on startup)
python -m app.cli seed-demo        ingest the fictional demo corpus and create its snapshot
python -m app.cli search "text"    run evidence search as the demo admin
python -m app.cli export-openapi   write packages/contracts/openapi.json
"""

import argparse
import json
import sys

from app.config import REPO_ROOT, get_settings

API_ROOT = REPO_ROOT / "services" / "api"


def cmd_migrate(_: argparse.Namespace) -> int:
    from alembic import command
    from alembic.config import Config

    cfg = Config(str(API_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(API_ROOT / "migrations"))
    command.upgrade(cfg, "head")
    return 0


def cmd_seed_demo(_: argparse.Namespace) -> int:
    from app.persistence.db import new_session
    from app.retrieval.embeddings import get_embedder
    from app.seed import seed_demo
    from app.storage import get_storage

    with new_session() as session, session.begin():
        report = seed_demo(session, storage=get_storage(), embedder=get_embedder())
    print(f"Created {len(report.created)} versions: {', '.join(report.created) or '-'}")
    print(f"Already present: {', '.join(report.skipped) or '-'}")
    print(f"Snapshot: {report.snapshot_id}")
    return 0


def cmd_search(args: argparse.Namespace) -> int:
    from app.domain.contracts import SearchRequest
    from app.persistence.db import new_session
    from app.retrieval.embeddings import get_embedder
    from app.retrieval.search import search
    from app.seed import DEMO_ORG_ID

    with new_session() as session:
        result = search(
            session,
            DEMO_ORG_ID,
            SearchRequest(question=args.question, limit=args.limit),
            get_embedder(),
        )
    print(f"snapshot={result.policy_snapshot_id} channels={result.channels} {result.latency_ms}ms")
    for hit in result.hits:
        c = hit.clause
        print(
            f"{hit.score:.4f} lex={hit.lexical_rank} dense={hit.dense_rank} "
            f"{hit.policy_title} {hit.version_label} §{c.section_path[-1]} {c.heading} "
            f"(page {c.page_index + 1})"
        )
    return 0


def cmd_export_openapi(args: argparse.Namespace) -> int:
    from app.main import app

    out = REPO_ROOT / "packages" / "contracts" / "openapi.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(app.openapi(), indent=2, ensure_ascii=False) + "\n"
    if args.check:
        if not out.exists() or out.read_text(encoding="utf-8") != text:
            print("packages/contracts/openapi.json is out of date; run export-openapi")
            return 1
        return 0
    out.write_text(text, encoding="utf-8", newline="\n")
    print(f"Wrote {out.relative_to(REPO_ROOT)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("migrate").set_defaults(fn=cmd_migrate)
    sub.add_parser("seed-demo").set_defaults(fn=cmd_seed_demo)
    p = sub.add_parser("search")
    p.add_argument("question")
    p.add_argument("--limit", type=int, default=8)
    p.set_defaults(fn=cmd_search)
    p = sub.add_parser("export-openapi")
    p.add_argument("--check", action="store_true", help="fail if the committed file is stale")
    p.set_defaults(fn=cmd_export_openapi)
    args = parser.parse_args(argv)
    get_settings()  # fail fast on invalid configuration
    code: int = args.fn(args)
    return code


if __name__ == "__main__":
    sys.exit(main())
