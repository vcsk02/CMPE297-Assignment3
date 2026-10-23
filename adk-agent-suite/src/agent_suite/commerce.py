"""Order domain: the model may prepare a quote; only an authenticated caller commits it."""

import time
import uuid

from agent_suite.storage import Database


class DomainError(ValueError):
    pass


class Shop:
    def __init__(self, db: Database, customer: str):
        if not customer:
            raise DomainError("Customer identity is required")
        self.db, self.customer = db, customer

    def search_products(self, query: str, max_price_cents: int = 100000) -> dict:
        if len(query) > 100 or not 1 <= max_price_cents <= 10000000:
            raise DomainError("Invalid search")
        # Literal substring search; SQL wildcard characters cannot broaden the request.
        query = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        with self.db.connection() as conn:
            rows = self.db.execute(
                conn,
                "SELECT * FROM products WHERE (LOWER(name) LIKE LOWER(?) ESCAPE '\\' "
                "OR LOWER(category) LIKE LOWER(?) ESCAPE '\\') AND price_cents<=? "
                "ORDER BY price_cents,id LIMIT 20",
                (f"%{query}%", f"%{query}%", max_price_cents),
            ).fetchall()
        return {"currency": "USD", "products": [dict(r) for r in rows]}

    def find_stores(self, city: str) -> dict:
        with self.db.connection() as conn:
            rows = self.db.execute(
                conn, "SELECT * FROM stores WHERE LOWER(city)=LOWER(?) LIMIT 20", (city[:100],)
            ).fetchall()
        return {"stores": [dict(r) for r in rows]}

    def prepare_order(self, product_id: str, quantity: int) -> dict:
        if type(quantity) is not int or not 1 <= quantity <= 10:
            raise DomainError("Quantity must be between 1 and 10")
        with self.db.connection(write=True) as conn:
            product = self.db.execute(
                conn, "SELECT * FROM products WHERE id=?", (product_id,)
            ).fetchone()
            if product is None or product["stock"] < quantity:
                raise DomainError("Product unavailable or insufficient stock")
            quote_id = "quote-" + uuid.uuid4().hex
            expiry = int(time.time()) + 600
            self.db.execute(
                conn,
                "INSERT INTO quotes VALUES (?,?,?,?,?,?)",
                (quote_id, self.customer, product_id, quantity, product["price_cents"], expiry),
            )
        return {
            "quote_id": quote_id,
            "product_id": product_id,
            "quantity": quantity,
            "unit_price_cents": product["price_cents"],
            "total_cents": product["price_cents"] * quantity,
            "currency": "USD",
            "expires_at": expiry,
            "requires_confirmation": True,
            "message": "No order placed. Confirm this exact quote through the trusted API or CLI.",
        }

    def confirm_order(self, quote_id: str, idempotency_key: str) -> dict:
        """Atomically validates ownership, expiry, price and stock, then creates one order."""
        if not 8 <= len(idempotency_key) <= 128:
            raise DomainError("Idempotency key must be 8 to 128 characters")
        with self.db.connection(write=True) as conn:
            replay = self.db.execute(
                conn,
                "SELECT * FROM orders WHERE customer=? AND idempotency_key=?",
                (self.customer, idempotency_key),
            ).fetchone()
            if replay:
                if replay["quote_id"] != quote_id:
                    raise DomainError("Idempotency key already belongs to a different quote")
                return dict(replay)
            quote = self.db.execute(
                conn,
                self.db.locked("SELECT * FROM quotes WHERE id=? AND customer=?"),
                (quote_id, self.customer),
            ).fetchone()
            if quote is None:
                raise DomainError("Quote not found")
            existing = self.db.execute(
                conn, "SELECT * FROM orders WHERE quote_id=?", (quote_id,)
            ).fetchone()
            if existing:
                return dict(existing)
            if quote["expires_at"] <= int(time.time()):
                raise DomainError("Quote expired; request a new quote")
            product = self.db.execute(
                conn, self.db.locked("SELECT * FROM products WHERE id=?"), (quote["product_id"],)
            ).fetchone()
            if product["price_cents"] != quote["price_cents"]:
                raise DomainError("Price changed; request a new quote")
            if product["stock"] < quote["quantity"]:
                raise DomainError("Insufficient stock")
            self.db.execute(
                conn,
                "UPDATE products SET stock=stock-? WHERE id=?",
                (quote["quantity"], quote["product_id"]),
            )
            order_id = "order-" + uuid.uuid4().hex
            # Orders record intent only. This application does not capture payment.
            self.db.execute(
                conn,
                "INSERT INTO orders VALUES (?,?,?,?,?,?,?,?)",
                (
                    order_id,
                    quote_id,
                    self.customer,
                    quote["price_cents"] * quote["quantity"],
                    "confirmed_unpaid",
                    "standard",
                    1,
                    idempotency_key,
                ),
            )
            return dict(
                self.db.execute(conn, "SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
            )

    def get_order(self, order_id: str) -> dict:
        with self.db.connection() as conn:
            row = self.db.execute(
                conn, "SELECT * FROM orders WHERE id=? AND customer=?", (order_id, self.customer)
            ).fetchone()
        if row is None:
            raise DomainError("Order not found")
        return dict(row)

    def update_delivery(self, order_id: str, delivery: str, expected_version: int) -> dict:
        if delivery not in {"pickup", "standard", "express"}:
            raise DomainError("Invalid delivery method")
        with self.db.connection(write=True) as conn:
            result = self.db.execute(
                conn,
                "UPDATE orders SET delivery=?,version=version+1 WHERE id=? AND customer=? "
                "AND version=? AND status='confirmed_unpaid'",
                (delivery, order_id, self.customer, expected_version),
            )
            if result.rowcount != 1:
                raise DomainError("Order not found or version conflict")
        return self.get_order(order_id)
