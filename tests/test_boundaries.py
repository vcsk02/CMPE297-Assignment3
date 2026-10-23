import asyncio
import json
import os
import sys

import pytest
from fastapi.testclient import TestClient

from agent_suite.api import create_app
from agent_suite.bugs import BugDesk
from agent_suite.commerce import DomainError, Shop
from agent_suite.paths import source_snapshot
from agent_suite.process import run_process
from agent_suite.research import DEMO_EVIDENCE, validate_lead_report
from agent_suite.review import ast_findings


def test_path_escape_and_symlink_rejected(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    (root / "link").symlink_to(tmp_path, target_is_directory=True)
    for target in ("../", str(tmp_path), "link"):
        with pytest.raises(ValueError):
            source_snapshot(root, target)


def test_snapshot_drops_env_and_instruction_files(tmp_path):
    (tmp_path / "p").mkdir()
    for filename in ("safe.py", ".env", "GEMINI.md", "AGENTS.md"):
        (tmp_path / "p" / filename).write_text("secret")
    assert list(source_snapshot(tmp_path, "p")) == ["safe.py"]


async def test_process_timeout_and_output_limit(tmp_path):
    with pytest.raises(TimeoutError):
        await run_process(
            [sys.executable, "-c", "import time; time.sleep(20)"],
            cwd=str(tmp_path),
            env=dict(os.environ),
            timeout=1,
        )
    with pytest.raises(ValueError, match="output limit"):
        await run_process(
            [sys.executable, "-c", "print('a'*50000)"],
            cwd=str(tmp_path),
            env=dict(os.environ),
            timeout=5,
            max_bytes=1024,
        )
    await asyncio.sleep(0)  # Let subprocess transports settle after cleanup.


def test_research_rejects_invented_citations():
    raw = {
        "market": "test",
        "patterns": [],
        "limitations": [],
        "leads": [
            {
                "company": "Test",
                "website": "https://test.example/",
                "signals": ["hiring"],
                "citations": ["https://invented.example/"],
                "rationale": "A purported hiring signal.",
            }
        ],
    }
    with pytest.raises(ValueError, match="citation absent"):
        validate_lead_report(raw, DEMO_EVIDENCE, "demo")


def test_syntax_error_is_reported():
    assert ast_findings({"bad.py": "def broken(:"})[0]["rule"] == "syntax"


def test_bug_draft_requires_confirmation_and_is_tenant_scoped(db):
    alice, bob = BugDesk(db, "alice-bug"), BugDesk(db, "bob-bug")
    draft = alice.propose_issue(
        "Cart quantity mismatch", "Expected cart quantity two; observed quantity one."
    )
    assert not alice.search_issues("quantity")["issues"]
    with pytest.raises(DomainError):
        bob.confirm_issue(draft["draft_id"])
    issue = alice.confirm_issue(draft["draft_id"])
    assert alice.confirm_issue(draft["draft_id"])["id"] == issue["id"]
    with pytest.raises(DomainError):
        bob.get_issue(issue["id"])


def test_api_requires_auth_and_uses_identity(settings, db, monkeypatch):
    token = "demo-test-token-123456789012345"
    monkeypatch.setenv("API_TOKENS", json.dumps({token: "api-alice"}))
    app = create_app(settings)
    with TestClient(app) as client:
        assert client.get("/healthz").status_code == 200
        assert client.post("/v1/agents/shop", json={"prompt": "buy"}).status_code == 401
        headers = {"Authorization": "Bearer " + token, "Idempotency-Key": "api-checkout-key"}
        quote = Shop(db, "api-alice").prepare_order("SHOE-001", 1)
        response = client.post(f"/v1/orders/{quote['quote_id']}/confirm", headers=headers)
        assert response.status_code == 200 and response.json()["customer"] == "api-alice"
        other = Shop(db, "other-user").prepare_order("SHOE-001", 1)
        assert (
            client.post(f"/v1/orders/{other['quote_id']}/confirm", headers=headers).status_code
            == 409
        )
        assert (
            client.post(
                "/v1/agents/shop", headers=headers, json={"prompt": "buy", "customer": "other-user"}
            ).status_code
            == 422
        )


def test_empty_token_configuration_fails_closed(settings, monkeypatch):
    monkeypatch.setenv("API_TOKENS", "{}")
    with TestClient(create_app(settings)) as client:
        assert (
            client.get("/v1/orders/anything", headers={"Authorization": "Bearer guess"}).status_code
            == 401
        )
