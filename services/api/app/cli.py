"""Operational commands (plan §15.4).

python -m app.cli db-start         start the local PostgreSQL (created on first use)
python -m app.cli db-stop          stop it
python -m app.cli db-status        show whether it is running
python -m app.cli migrate          apply database migrations (explicit; never on startup)
python -m app.cli seed-demo        ingest the fictional demo corpus and create its snapshot
python -m app.cli search "text"    run evidence search as the demo admin
python -m app.cli export-openapi   write packages/contracts/openapi.json
python -m app.cli evaluate         measure retrieval (and assessments, if a model is set)
python -m app.cli check-model      send one small request to the configured model gateway
"""

import argparse
import json
import os
import sys
import time

from app.config import REPO_ROOT, get_settings

API_ROOT = REPO_ROOT / "services" / "api"


def cmd_db(args: argparse.Namespace) -> int:
    from app import localdb

    action = {"db-start": localdb.start, "db-stop": localdb.stop, "db-status": localdb.status}
    try:
        print(action[args.command]())
    except localdb.LocalDbError as exc:
        print(exc)
        return 1
    return 0


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


def cmd_evaluate(args: argparse.Namespace) -> int:
    """Runs against `<database>_eval` (created, migrated and seeded here) so evaluation cases
    never appear in the demo database."""
    from app.evaluation import select_scenarios

    try:
        select_scenarios(args.split, args.limit)
    except (ValueError, FileNotFoundError) as exc:
        print(f"Cannot evaluate: {exc}")
        return 1

    from sqlalchemy.engine import make_url

    from app.persistence.db import ensure_database

    base = make_url(get_settings().database_url)
    if not args.same_database:
        eval_url = base.set(database=f"{base.database}_eval")
        ensure_database(eval_url)
        os.environ["DATABASE_URL"] = eval_url.render_as_string(hide_password=False)
        get_settings.cache_clear()
    cmd_migrate(args)
    cmd_seed_demo(args)

    from app.evaluation import evaluate, write_report
    from app.retrieval.embeddings import get_embedder
    from app.workflow.llm import get_model_client

    model = None if args.retrieval_only else get_model_client()
    summary, results = evaluate(args.split, model=model, embedder=get_embedder(), limit=args.limit)
    report, raw = write_report(summary, results)
    print(f"Wrote {report.relative_to(REPO_ROOT)} and {raw.relative_to(REPO_ROOT)}")
    return 0


def cmd_check_model(_: argparse.Namespace) -> int:
    """One small structured request through the same client the workflow uses, to confirm
    the gateway URL, key, model alias and JSON mode before running an assessment."""
    from pydantic import BaseModel

    from app.workflow.llm import SETUP_HINT, CallBudget, ModelError, get_model_client

    class Ping(BaseModel):
        reply: str

    model = get_model_client()
    if model is None:
        print(f"No language model is configured. {SETUP_HINT}")
        return 1
    s = get_settings()
    print(f"Model {model.name} at {s.llm_base_url} (JSON mode {s.llm_json_mode})")
    budget = CallBudget(model, max_calls=2, deadline_seconds=s.run_deadline_seconds)
    started = time.monotonic()
    try:
        out = budget.structured(
            "connection_check",
            "You are a connection test. Reply in JSON.",
            'Set "reply" to the word ok.',
            Ping,
        )
    except ModelError as exc:
        print(f"Failed: {exc.code}: {exc.message}")
        return 1
    usage = budget.usage()
    print(
        f"OK in {time.monotonic() - started:.1f}s: reply={out.reply!r} "
        f"served_model={usage['served_model'] or 'not reported'} calls={usage['model_calls']} "
        f"tokens_in={usage['input_tokens']} tokens_out={usage['output_tokens']}"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("db-start", "db-stop", "db-status"):
        sub.add_parser(name).set_defaults(fn=cmd_db)
    sub.add_parser("migrate").set_defaults(fn=cmd_migrate)
    sub.add_parser("seed-demo").set_defaults(fn=cmd_seed_demo)
    p = sub.add_parser("search")
    p.add_argument("question")
    p.add_argument("--limit", type=int, default=8)
    p.set_defaults(fn=cmd_search)
    p = sub.add_parser("export-openapi")
    p.add_argument("--check", action="store_true", help="fail if the committed file is stale")
    p.set_defaults(fn=cmd_export_openapi)
    p = sub.add_parser("evaluate")
    p.add_argument("--split", default="dev", choices=["dev", "test"])
    p.add_argument("--limit", type=int, default=None, help="only the first N scenarios")
    p.add_argument("--retrieval-only", action="store_true", help="skip model calls")
    p.add_argument("--same-database", action="store_true", help="use DATABASE_URL as is")
    p.set_defaults(fn=cmd_evaluate)
    sub.add_parser("check-model").set_defaults(fn=cmd_check_model)
    args = parser.parse_args(argv)
    get_settings()  # fail fast on invalid configuration
    code: int = args.fn(args)
    return code


if __name__ == "__main__":
    sys.exit(main())
