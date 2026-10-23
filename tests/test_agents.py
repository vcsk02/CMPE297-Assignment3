import pytest

from agent_suite.cli import DEMO_PROMPTS
from agent_suite.runtime import run_agent


@pytest.mark.parametrize("kind", ["leads", "cli", "bugs", "review", "shop"])
async def test_real_adk_end_to_end(kind, trusted_settings):
    result = await run_agent(kind, DEMO_PROMPTS[kind], trusted_settings)
    assert result["mode"] == "demo"
    assert result["session_id"]
    if kind == "leads":
        assert len(result["output"]["leads"]) == 2
        assert len(result["output"]["sources"]) == 3
        calls = [c["name"] for t in result["trace"] for c in t["calls"]]
        assert calls.count("search_web") == 2 and "finish_research" in calls
    elif kind == "review":
        assert result["output"]["verdict"] == "changes_requested"
        assert result["output"]["test_execution"]["status"] == "failed"
        rules = {f["rule"] for f in result["output"]["findings"]}
        assert {"stack-initialization", "sql-interpolation", "shell-true"} <= rules
    elif kind == "shop":
        assert result["output"]["quote"]["total_cents"] == 12900
        assert result["output"]["quote"]["requires_confirmation"]
    else:
        assert len(result["trace"]) >= 2
