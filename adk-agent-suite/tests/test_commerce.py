from concurrent.futures import ThreadPoolExecutor

import pytest

from agent_suite.commerce import DomainError, Shop


def test_confirmation_is_idempotent_and_decrements_once(db):
    shop = Shop(db, "demo_customer")
    before = shop.search_products("running")["products"][0]["stock"]
    quote = shop.prepare_order("SHOE-001", 1)
    first = shop.confirm_order(quote["quote_id"], "checkout-0001")
    second = shop.confirm_order(quote["quote_id"], "checkout-0001")
    assert first == second
    assert first["total_cents"] == 12900
    assert first["status"] == "confirmed_unpaid"
    assert shop.search_products("running")["products"][0]["stock"] == before - 1


def test_cross_customer_quote_and_order_access_denied(db):
    alice, bob = Shop(db, "alice"), Shop(db, "bob")
    quote = alice.prepare_order("SHOE-001", 1)
    with pytest.raises(DomainError, match="Quote not found"):
        bob.confirm_order(quote["quote_id"], "bob-checkout")
    order = alice.confirm_order(quote["quote_id"], "alice-checkout")
    with pytest.raises(DomainError, match="Order not found"):
        bob.get_order(order["id"])
    with pytest.raises(DomainError):
        bob.update_delivery(order["id"], "pickup", 1)


def test_expired_quote_and_price_change_fail_closed(db):
    shop = Shop(db, "expiry-test")
    quote = shop.prepare_order("SHOE-001", 1)
    with db.connection(write=True) as conn:
        db.execute(conn, "UPDATE quotes SET expires_at=0 WHERE id=?", (quote["quote_id"],))
    with pytest.raises(DomainError, match="expired"):
        shop.confirm_order(quote["quote_id"], "expired-key")
    quote = shop.prepare_order("SHOE-001", 1)
    with db.connection(write=True) as conn:
        db.execute(conn, "UPDATE products SET price_cents=13000 WHERE id='SHOE-001'")
    try:
        with pytest.raises(DomainError, match="Price changed"):
            shop.confirm_order(quote["quote_id"], "changed-price-key")
    finally:
        with db.connection(write=True) as conn:
            db.execute(conn, "UPDATE products SET price_cents=12900 WHERE id='SHOE-001'")


def test_concurrent_last_item_never_oversells(db):
    with db.connection(write=True) as conn:
        db.execute(conn, "UPDATE products SET stock=1 WHERE id='BAG-001'")
    shops = [Shop(db, f"concurrent-{i}") for i in range(8)]
    quotes = [s.prepare_order("BAG-001", 1) for s in shops]

    def confirm(item):
        index, shop = item
        try:
            return shop.confirm_order(quotes[index]["quote_id"], f"concurrent-key-{index}")
        except DomainError:
            return None

    try:
        with ThreadPoolExecutor(max_workers=8) as pool:
            orders = list(pool.map(confirm, enumerate(shops)))
        assert sum(o is not None for o in orders) == 1
        assert shops[0].search_products("backpack")["products"][0]["stock"] == 0
    finally:
        with db.connection(write=True) as conn:
            db.execute(conn, "UPDATE products SET stock=5 WHERE id='BAG-001'")


def test_quote_replay_with_new_key_still_one_order(db):
    shop = Shop(db, "new-key-test")
    quote = shop.prepare_order("BALL-001", 1)
    first = shop.confirm_order(quote["quote_id"], "first-key")
    assert shop.confirm_order(quote["quote_id"], "second-key")["id"] == first["id"]
    other = shop.prepare_order("BALL-001", 1)
    with pytest.raises(DomainError, match="different quote"):
        shop.confirm_order(other["quote_id"], "first-key")


def test_delivery_uses_optimistic_version(db):
    shop = Shop(db, "delivery-test")
    quote = shop.prepare_order("BALL-001", 1)
    order = shop.confirm_order(quote["quote_id"], "delivery-key")
    updated = shop.update_delivery(order["id"], "pickup", 1)
    assert updated["version"] == 2 and updated["delivery"] == "pickup"
    with pytest.raises(DomainError, match="version conflict"):
        shop.update_delivery(order["id"], "express", 1)


@pytest.mark.parametrize("quantity", [0, -1, 11, True])
def test_invalid_quantity(db, quantity):
    with pytest.raises(DomainError):
        Shop(db, "demo_customer").prepare_order("SHOE-001", quantity)


def test_sql_input_is_literal(db):
    assert Shop(db, "demo_customer").search_products("' OR 1=1 --")["products"] == []
    assert Shop(db, "demo_customer").search_products("%")["products"] == []
