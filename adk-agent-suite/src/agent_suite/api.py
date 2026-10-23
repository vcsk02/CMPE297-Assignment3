"""Authenticated API. Confirmation is a caller action, deliberately absent from model tools."""

import asyncio
import logging
import secrets
import uuid
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from agent_suite.bugs import BugDesk
from agent_suite.commerce import DomainError, Shop
from agent_suite.config import Settings, api_identities
from agent_suite.runtime import run_agent
from agent_suite.schemas import AgentRequest, DeliveryUpdate
from agent_suite.storage import Database, StorageConflict

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    identities = api_identities()
    db = Database(settings.database_path, settings.database_url)
    semaphore = asyncio.Semaphore(settings.concurrency)

    @asynccontextmanager
    async def lifespan(app):
        db.initialize()
        yield

    app = FastAPI(title="ADK Agent Suite", version="1.0.0", lifespan=lifespan)
    bearer = HTTPBearer(auto_error=False)

    def identity(
        credentials: HTTPAuthorizationCredentials | None = Depends(bearer),  # noqa: B008
    ) -> str:
        if credentials and credentials.scheme.lower() == "bearer":
            for token, customer in identities.items():
                if secrets.compare_digest(credentials.credentials, token):
                    return customer
        raise HTTPException(status_code=401, detail="Valid bearer token required")

    @app.middleware("http")
    async def request_id(request: Request, call_next):
        run_id = uuid.uuid4().hex
        try:
            length = int(request.headers.get("content-length", "0"))
        except ValueError:
            return JSONResponse(status_code=400, content={"detail": "Invalid content length"})
        if length > 32000:
            return JSONResponse(status_code=413, content={"detail": "Request body too large"})
        response = await call_next(request)
        response.headers["X-Request-ID"] = run_id
        return response

    @app.exception_handler(StorageConflict)
    @app.exception_handler(DomainError)
    async def domain_error(request, exc):
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    @app.get("/healthz")
    def health():
        return {"status": "ok", "mode": settings.mode}

    @app.post("/v1/agents/{kind}")
    async def invoke(kind: str, body: AgentRequest, customer: str = Depends(identity)):
        if kind not in {"leads", "cli", "bugs", "review", "shop"}:
            raise HTTPException(404, "Unknown agent")
        try:
            await asyncio.wait_for(semaphore.acquire(), timeout=0.1)
        except TimeoutError as error:
            raise HTTPException(429, "Agent capacity reached; retry later") from error
        try:
            return await run_agent(kind, body.prompt, settings, customer, body.target)
        except TimeoutError as error:
            raise HTTPException(504, "Agent execution timed out") from error
        except ValueError as error:
            raise HTTPException(422, str(error)) from error
        except Exception as error:
            # Exception text may contain provider data. Keep the public response generic.
            logger.error("agent_failed type=%s agent=%s", type(error).__name__, kind)
            raise HTTPException(
                502, "Agent execution failed; inspect server diagnostics"
            ) from error
        finally:
            semaphore.release()

    @app.post("/v1/orders/{quote_id}/confirm")
    def confirm(
        quote_id: str,
        customer: str = Depends(identity),
        idempotency_key: str = Header(alias="Idempotency-Key", min_length=8, max_length=128),
    ):
        return Shop(db, customer).confirm_order(quote_id, idempotency_key)

    @app.get("/v1/orders/{order_id}")
    def status(order_id: str, customer: str = Depends(identity)):
        return Shop(db, customer).get_order(order_id)

    @app.patch("/v1/orders/{order_id}/delivery")
    def delivery(order_id: str, body: DeliveryUpdate, customer: str = Depends(identity)):
        return Shop(db, customer).update_delivery(order_id, body.delivery, body.expected_version)

    @app.post("/v1/bugs/{draft_id}/confirm")
    def confirm_bug(draft_id: str, customer: str = Depends(identity)):
        return BugDesk(db, customer).confirm_issue(draft_id)

    return app
