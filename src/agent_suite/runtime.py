"""One invocation = fresh ADK graph, persisted session and bounded execution budget."""

import asyncio
import json
import logging
import time
import uuid
from pathlib import Path

from google.adk.agents.run_config import RunConfig
from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService
from google.genai import types

from agent_suite.agents import build_agent
from agent_suite.config import Settings
from agent_suite.research import validate_lead_report
from agent_suite.review import final_review

logger = logging.getLogger(__name__)


def objects_in(value):
    """Unwrap standard MCP content/structuredContent without assuming a transport-specific envelope."""
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from objects_in(child)
    elif isinstance(value, list):
        for child in value:
            yield from objects_in(child)
    elif isinstance(value, str) and value.lstrip().startswith(("{", "[")):
        try:
            yield from objects_in(json.loads(value))
        except json.JSONDecodeError:
            pass


async def run_agent(
    kind: str,
    prompt: str,
    settings: Settings,
    identity: str = "demo_customer",
    target: str = "review_target",
) -> dict:
    if not 1 <= len(prompt) <= 6000:
        raise ValueError("Prompt length must be 1 to 6000 characters")
    Path(settings.database_path).parent.mkdir(parents=True, exist_ok=True)
    agent, toolsets = build_agent(kind, settings, identity)
    sessions = DatabaseSessionService(db_url=settings.session_database_url)
    session_id, started = uuid.uuid4().hex, time.monotonic()
    runner = Runner(app_name="agent_suite", agent=agent, session_service=sessions)
    traces, texts, usage = [], [], {"prompt_tokens": 0, "output_tokens": 0}
    try:
        await sessions.create_session(
            app_name="agent_suite",
            user_id=identity,
            session_id=session_id,
            state={
                "review_target": target,
                "research_evidence": [],
                "research_critique": "Initial research",
                "search_count": 0,
                "user:customer_id": identity,
            },
        )
        async with asyncio.timeout(settings.request_timeout):
            async for event in runner.run_async(
                user_id=identity,
                session_id=session_id,
                new_message=types.Content(role="user", parts=[types.Part.from_text(text=prompt)]),
                run_config=RunConfig(max_llm_calls=24),
            ):
                entry = {"author": event.author, "calls": [], "responses": []}
                for part in event.content.parts if event.content else []:
                    if part.function_call:
                        entry["calls"].append(
                            {"name": part.function_call.name, "arguments": part.function_call.args}
                        )
                    if part.function_response:
                        entry["responses"].append(
                            {
                                "name": part.function_response.name,
                                "data": part.function_response.response,
                            }
                        )
                    if part.text and not part.thought:
                        texts.append({"author": event.author, "text": part.text})
                if event.usage_metadata:
                    usage["prompt_tokens"] += event.usage_metadata.prompt_token_count or 0
                    usage["output_tokens"] += event.usage_metadata.candidates_token_count or 0
                if entry["calls"] or entry["responses"]:
                    traces.append(entry)
        session = await sessions.get_session(
            app_name="agent_suite", user_id=identity, session_id=session_id
        )
        state = session.state
        if kind == "leads":
            output = validate_lead_report(
                state["lead_report"], state["research_evidence"], settings.mode
            )
        elif kind == "review":
            output = final_review(state, state["review_narrative"])
        else:
            output = {"message": texts[-1]["text"] if texts else "No final response"}
        if kind == "shop":
            quotes = [
                obj for obj in objects_in(traces) if "quote_id" in obj and "expires_at" in obj
            ]
            output["quote"] = quotes[-1] if quotes else None
        result = {
            "agent": kind,
            "mode": settings.mode,
            "model": "scripted-offline-fixture" if settings.mode == "demo" else settings.model,
            "session_id": session_id,
            "output": output,
            "trace": traces,
            "messages": texts,
            "usage": usage,
            "elapsed_seconds": round(time.monotonic() - started, 3),
        }
        logger.info(
            json.dumps(
                {
                    "event": "agent.complete",
                    "agent": kind,
                    "mode": settings.mode,
                    "session_id": session_id,
                    "elapsed_seconds": result["elapsed_seconds"],
                    "tool_events": len(traces),
                    **usage,
                }
            )
        )
        return result
    finally:
        for tools in reversed(toolsets):
            await tools.close()
        await runner.close()
        # SQLAlchemy pools should not leak file descriptors across repeated invocations.
        await sessions.close()
