"""Tenant-scoped issue triage, knowledge search and explicit draft confirmation."""

import uuid

from agent_suite.commerce import DomainError
from agent_suite.storage import Database

KNOWLEDGE = [
    {
        "id": "KB-001",
        "title": "Checkout idempotency",
        "text": "Use an idempotency key scoped to the customer. In one transaction, lock inventory, "
        "validate the quote and persist the order with a unique customer/key constraint. "
        "Regression: repeat a request and verify the same order ID and one stock decrement.",
    },
    {
        "id": "KB-002",
        "title": "Session expiry",
        "text": "Compare cookie max-age, server TTL and clock skew. Never include session tokens in a ticket.",
    },
]


class BugDesk:
    def __init__(self, db: Database, tenant: str):
        if not tenant:
            raise DomainError("Tenant identity is required")
        self.db, self.tenant = db, tenant

    def search_issues(self, query: str) -> dict:
        # Filtering in Python keeps literal matching portable and the dataset bounded.
        with self.db.connection() as conn:
            rows = self.db.execute(
                conn, "SELECT * FROM issues WHERE tenant=? ORDER BY id LIMIT 500", (self.tenant,)
            ).fetchall()
        terms = query.lower().split()[:12]
        rows = [
            dict(r) for r in rows if any(t in (r["title"] + " " + r["body"]).lower() for t in terms)
        ]
        return {"issues": rows[:20]}

    def get_issue(self, issue_id: str) -> dict:
        with self.db.connection() as conn:
            row = self.db.execute(
                conn, "SELECT * FROM issues WHERE id=? AND tenant=?", (issue_id, self.tenant)
            ).fetchone()
        if row is None:
            raise DomainError("Issue not found")
        return dict(row)

    def search_knowledge(self, query: str) -> dict:
        terms = query.lower().split()[:12]
        return {
            "articles": [
                a
                for a in KNOWLEDGE
                if any(t in (a["title"] + " " + a["text"]).lower() for t in terms)
            ]
        }

    def propose_issue(self, title: str, body: str) -> dict:
        if not 5 <= len(title) <= 160 or not 20 <= len(body) <= 6000:
            raise DomainError("Invalid title or body length")
        draft_id = "draft-" + uuid.uuid4().hex
        with self.db.connection(write=True) as conn:
            self.db.execute(
                conn,
                "INSERT INTO bug_drafts VALUES (?,?,?,?,NULL)",
                (draft_id, self.tenant, title, body),
            )
        return {
            "draft_id": draft_id,
            "title": title,
            "body": body,
            "requires_confirmation": True,
            "backend": "local_issue_tracker",
        }

    def confirm_issue(self, draft_id: str) -> dict:
        with self.db.connection(write=True) as conn:
            draft = self.db.execute(
                conn,
                self.db.locked("SELECT * FROM bug_drafts WHERE id=? AND tenant=?"),
                (draft_id, self.tenant),
            ).fetchone()
            if draft is None:
                raise DomainError("Draft not found")
            issue_id = draft["issue_id"] or "BUG-" + uuid.uuid4().hex[:12]
            if not draft["issue_id"]:
                self.db.execute(
                    conn,
                    "INSERT INTO issues VALUES (?,?,?,?,?)",
                    (issue_id, self.tenant, draft["title"], draft["body"], "open"),
                )
                self.db.execute(
                    conn, "UPDATE bug_drafts SET issue_id=? WHERE id=?", (issue_id, draft_id)
                )
        return self.get_issue(issue_id)
