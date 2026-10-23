"""Real MCP stdio server. Identity comes from its trusted parent process, never tool arguments."""

import argparse
import logging
import os

from mcp.server.fastmcp import FastMCP

from agent_suite.bugs import BugDesk
from agent_suite.commerce import Shop
from agent_suite.storage import Database


def build_server(kind: str) -> FastMCP:
    db = Database(os.environ["SUITE_MCP_DB_PATH"], os.getenv("SUITE_MCP_DATABASE_URL", ""))
    identity = os.environ["SUITE_MCP_IDENTITY"]
    server = FastMCP("agent-suite-" + kind)
    if kind == "bugs":
        desk = BugDesk(db, identity)

        @server.tool()
        def search_issues(query: str) -> dict:
            """Find related issues in the authenticated tenant's tracker."""
            return desk.search_issues(query)

        @server.tool()
        def get_issue(issue_id: str) -> dict:
            """Read one issue belonging to the authenticated tenant."""
            return desk.get_issue(issue_id)

        @server.tool()
        def search_knowledge(query: str) -> dict:
            """Search troubleshooting articles and cite their KB IDs."""
            return desk.search_knowledge(query)

        @server.tool()
        def propose_issue(title: str, body: str) -> dict:
            """Save a draft for operator review; this does not create an issue."""
            return desk.propose_issue(title, body)
    elif kind == "shop":
        shop = Shop(db, identity)

        @server.tool()
        def search_products(query: str, max_price_cents: int = 100000) -> dict:
            """Search catalog. All money is integer USD cents."""
            return shop.search_products(query, max_price_cents)

        @server.tool()
        def find_stores(city: str) -> dict:
            """Find stores by city; demo store addresses are fictional."""
            return shop.find_stores(city)

        @server.tool()
        def prepare_order(product_id: str, quantity: int) -> dict:
            """Prepare an expiring quote. Never claims a completed order or payment."""
            return shop.prepare_order(product_id, quantity)

        @server.tool()
        def get_order(order_id: str) -> dict:
            """Read order status scoped to the authenticated customer."""
            return shop.get_order(order_id)
    else:
        raise ValueError("Unknown MCP server")
    return server


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("kind", choices=["bugs", "shop"])
    args = parser.parse_args()
    # Stdout belongs exclusively to MCP JSON-RPC; logs go to stderr.
    logging.basicConfig(level=logging.WARNING)
    build_server(args.kind).run(transport="stdio")


if __name__ == "__main__":
    main()
