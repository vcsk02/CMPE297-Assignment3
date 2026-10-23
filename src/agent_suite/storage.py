"""Small portable SQL layer. All user values use bound parameters."""

import sqlite3
from contextlib import contextmanager
from pathlib import Path


class StorageConflict(ValueError):
    """Constraint collision; callers may retry their original idempotent request."""


class Database:
    def __init__(self, path: str = "data/suite.db", url: str = ""):
        self.path, self.url = str(Path(path).resolve()), url
        self.postgres = bool(url)
        if not self.postgres:
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def connection(self, write: bool = False):
        if self.postgres:
            import psycopg
            from psycopg.rows import dict_row

            conn = psycopg.connect(self.url, row_factory=dict_row, connect_timeout=10)
        else:
            conn = sqlite3.connect(self.path, timeout=15, isolation_level=None)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys=ON")
            conn.execute("PRAGMA busy_timeout=15000")
            conn.execute("BEGIN IMMEDIATE" if write else "BEGIN")
        try:
            yield conn
            conn.commit()
        except BaseException:
            conn.rollback()
            raise
        finally:
            conn.close()

    def execute(self, conn, sql: str, params: tuple = ()):
        try:
            return conn.execute(sql.replace("?", "%s") if self.postgres else sql, params)
        except sqlite3.IntegrityError as error:
            raise StorageConflict("Database constraint conflict") from error
        except Exception as error:
            if self.postgres:
                import psycopg

                if isinstance(error, psycopg.IntegrityError):
                    raise StorageConflict("Database constraint conflict") from error
            raise

    def locked(self, sql: str) -> str:
        return sql + " FOR UPDATE" if self.postgres else sql

    def initialize(self):
        statements = [
            "CREATE TABLE IF NOT EXISTS products (id TEXT PRIMARY KEY, name TEXT NOT NULL, "
            "category TEXT NOT NULL, price_cents INTEGER NOT NULL CHECK(price_cents>0), "
            "stock INTEGER NOT NULL CHECK(stock>=0))",
            "CREATE TABLE IF NOT EXISTS stores (id TEXT PRIMARY KEY, city TEXT NOT NULL, "
            "address TEXT NOT NULL)",
            "CREATE TABLE IF NOT EXISTS quotes (id TEXT PRIMARY KEY, customer TEXT NOT NULL, "
            "product_id TEXT NOT NULL REFERENCES products(id), quantity INTEGER NOT NULL "
            "CHECK(quantity>0), price_cents INTEGER NOT NULL, expires_at BIGINT NOT NULL)",
            "CREATE TABLE IF NOT EXISTS orders (id TEXT PRIMARY KEY, quote_id TEXT UNIQUE NOT NULL "
            "REFERENCES quotes(id), customer TEXT NOT NULL, total_cents INTEGER NOT NULL, "
            "status TEXT NOT NULL, delivery TEXT NOT NULL, version INTEGER NOT NULL DEFAULT 1, "
            "idempotency_key TEXT NOT NULL, UNIQUE(customer,idempotency_key))",
            "CREATE TABLE IF NOT EXISTS issues (id TEXT PRIMARY KEY, tenant TEXT NOT NULL, "
            "title TEXT NOT NULL, body TEXT NOT NULL, status TEXT NOT NULL)",
            "CREATE TABLE IF NOT EXISTS bug_drafts (id TEXT PRIMARY KEY, tenant TEXT NOT NULL, "
            "title TEXT NOT NULL, body TEXT NOT NULL, issue_id TEXT UNIQUE)",
        ]
        with self.connection(write=True) as conn:
            for sql in statements:
                self.execute(conn, sql)

    def seed_demo(self):
        """Only explicit demo/test setup calls this; production startup never seeds."""
        self.initialize()
        with self.connection(write=True) as conn:
            for row in [
                ("SHOE-001", "Trail Runner Pro", "running", 12900, 8),
                ("BALL-001", "Match Football", "football", 3500, 20),
                ("BAG-001", "Training Backpack", "training", 5900, 5),
            ]:
                self.execute(
                    conn, "INSERT INTO products VALUES (?,?,?,?,?) ON CONFLICT DO NOTHING", row
                )
            self.execute(
                conn,
                "INSERT INTO stores VALUES (?,?,?) ON CONFLICT DO NOTHING",
                ("SJ-01", "San Jose", "100 Demo Avenue (fictional)"),
            )
            for row in [
                (
                    "BUG-101",
                    "demo_customer",
                    "Duplicate order after checkout retry",
                    "A network retry creates a second order. Reproduce by sending the same request twice.",
                    "open",
                ),
                (
                    "BUG-102",
                    "demo_customer",
                    "Login cookie expires early",
                    "Session cookie lifetime is shorter than the configured TTL.",
                    "open",
                ),
            ]:
                self.execute(
                    conn, "INSERT INTO issues VALUES (?,?,?,?,?) ON CONFLICT DO NOTHING", row
                )
