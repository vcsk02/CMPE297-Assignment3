"""Human-friendly executable entry points for all five agents and trusted confirmations."""

import argparse
import asyncio
import json
import logging
from dataclasses import replace
from pathlib import Path

from agent_suite.bugs import BugDesk
from agent_suite.commerce import Shop
from agent_suite.config import Settings
from agent_suite.runtime import run_agent
from agent_suite.storage import Database

DEMO_PROMPTS = {
    "leads": "Find Thailand fintech expansion leads and verify market-entry signals. Demo scenario.",
    "cli": "Analyze review_target, explain its DFS bug, and suggest regression tests. Demo scenario.",
    "bugs": "Checkout retries produce duplicate orders. Find duplicates and recommend a fix. Demo scenario.",
    "review": "Review the Python project for correctness and security. Demo scenario.",
    "shop": "Find running shoes under $150 in San Jose and prepare a quote for one pair. Demo scenario.",
}


def save(path: Path, result: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")


async def demo_all(settings: Settings, destination: Path):
    db = Database(settings.database_path, settings.database_url)
    db.seed_demo()
    index = {}
    for kind, prompt in DEMO_PROMPTS.items():
        result = await run_agent(kind, prompt, settings)
        save(destination / f"{kind}.json", result)
        index[kind] = {
            "file": f"{kind}.json",
            "elapsed_seconds": result["elapsed_seconds"],
            "tool_calls": sum(len(t["calls"]) for t in result["trace"]),
        }
        print(f"{kind:8} mode=demo saved={destination / (kind + '.json')}")
        if kind == "shop":
            quote = result["output"]["quote"]
            shop = Shop(db, "demo_customer")
            stock_before = shop.search_products("running")["products"][0]["stock"]
            order = shop.confirm_order(quote["quote_id"], "demo-checkout-key")
            replay = shop.confirm_order(quote["quote_id"], "demo-checkout-key")
            stock_after = shop.search_products("running")["products"][0]["stock"]
            if stock_after != stock_before - quote["quantity"]:
                raise AssertionError("Stock did not decrement exactly once")
            if order["id"] != replay["id"]:
                raise AssertionError("Checkout replay was not idempotent")
            save(
                destination / "shop_checkout.json",
                {
                    "quote": quote,
                    "order": order,
                    "replay_same_order": True,
                    "stock_decremented_once": True,
                    "confirmation_actor": "trusted demo driver, not model",
                    "payment_captured": False,
                },
            )
    save(
        destination / "index.json",
        {
            "mode": "demo",
            "backend": "scripted ADK model + real tools",
            "agents": index,
            "live_model_verified": False,
            "note": "MCP, ADK, SQLite, AST, Ruff and fixture subprocess actually execute.",
        },
    )


def main():
    parser = argparse.ArgumentParser(
        description="Five ADK agents: demo, run, serve and confirmations"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    demo = sub.add_parser("demo")
    demo.add_argument("--output", default="artifacts/demo")
    run = sub.add_parser("run")
    run.add_argument("agent", choices=list(DEMO_PROMPTS))
    run.add_argument("--prompt", required=True)
    run.add_argument("--mode", choices=["demo", "live"], default="live")
    run.add_argument("--target", default="review_target")
    run.add_argument("--identity", default="local_operator")
    run.add_argument("--output", default="artifacts/latest.json")
    serve = sub.add_parser("serve")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8080)
    sub.add_parser("init-db")
    for name in ("confirm-order", "confirm-bug"):
        command = sub.add_parser(name)
        command.add_argument("id")
        command.add_argument("--identity", required=True)
        if name == "confirm-order":
            command.add_argument("--idempotency-key", required=True)
    args = parser.parse_args()
    settings = Settings.from_env()
    logging.basicConfig(level=logging.WARNING)
    if args.command == "demo":
        # A separate database makes reruns reproducible and cannot alter a live store.
        destination = Path(args.output)
        destination.mkdir(parents=True, exist_ok=True)
        settings = replace(
            settings,
            mode="demo",
            database_url="",
            catalog_mcp_url="",
            database_path=str(destination / "demo.db"),
            session_database_url=f"sqlite+aiosqlite:///{destination / 'sessions.db'}",
            review_test_mode="trusted",
        )
        for name in ("demo.db", "sessions.db"):
            (destination / name).unlink(missing_ok=True)
        asyncio.run(demo_all(settings, destination))
    elif args.command == "run":
        settings = replace(settings, mode=args.mode)
        result = asyncio.run(
            run_agent(args.agent, args.prompt, settings, args.identity, args.target)
        )
        save(Path(args.output), result)
        print(json.dumps(result["output"], indent=2))
    elif args.command == "serve":
        import uvicorn

        from agent_suite.api import create_app

        uvicorn.run(create_app(settings), host=args.host, port=args.port, log_level="info")
    else:
        db = Database(settings.database_path, settings.database_url)
        if args.command == "init-db":
            db.initialize()
            print("Database initialized. No demonstration records inserted.")
        elif args.command == "confirm-order":
            print(
                json.dumps(
                    Shop(db, args.identity).confirm_order(args.id, args.idempotency_key), indent=2
                )
            )
        else:
            print(json.dumps(BugDesk(db, args.identity).confirm_issue(args.id), indent=2))


if __name__ == "__main__":
    main()
