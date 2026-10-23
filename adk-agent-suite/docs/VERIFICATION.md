# Verification record

This record describes what was actually exercised in the delivered environment.

| Area | Status | Evidence |
|---|---|---|
| Project tests on SQLite | Passed: 24 tests | `artifacts/test-results.xml` |
| Five ADK graphs | Executed through actual Runner | `artifacts/demo/*.json` |
| Lead research loop | Two searches plus loop termination; fictional web fixtures | `leads.json` trace |
| Gemini CLI tool | Real bounded subprocess using explicit fixture double | `cli.json` trace |
| External Gemini CLI installation | Version 0.65.0 and headless flags checked | pinned `package-lock.json`; `artifacts/cli-version.txt` |
| Bug-assistant MCP | Real stdio discovery and three tool calls | `bugs.json` trace |
| Code review | Real AST, Ruff, unittest; fixture faults detected | `review.json` |
| E-commerce MCP | Real catalog/store/quote calls | `shop.json` |
| Confirmation and replay | Same order returned; one stock decrement | `shop_checkout.json`, transaction tests |
| Last-item concurrency | Eight competing buyers; exactly one success | `test_concurrent_last_item_never_oversells` |
| Cross-customer access | Rejected for quote, order, delivery and bug draft | boundary/domain tests |
| HTTP authentication | Missing/incorrect tokens rejected; identity bound by server | boundary tests |
| Path/process boundaries | Escape, symlink, timeout and excessive output checked | boundary tests |
| Video | Rendered from actual source/results with synthetic narration | `video/` |
| Live Gemini/grounded search inference | Not run; no provider key supplied | live commands in walkthrough |
| PostgreSQL / AlloyDB | Adapter and CI job supplied; local server unavailable | CI workflow and integration guide |
| Remote MCP Toolbox | Optional connection and config supplied; hosted path not exercised | `integrations/toolbox/` |
| Docker / Cloud Run | Deployment assets supplied; not built/deployed here | Dockerfile, compose, deployment guide |
| GitHub publication | Not performed; publishing tools/auth absent in this session | publishing scripts |
| YouTube publication | Not performed; no authorized upload channel exposed | upload script and finished MP4 |

Environment: Python 3.12.14, Google ADK 2.12.0, MCP 1.30.0, Gemini CLI 0.65.0.
Direct and transitive Python versions are in `uv.lock`; the external CLI has its own
npm lock. These are tested versions, not an assurance that every later release works.

ADK emits deprecation warnings for SequentialAgent/ParallelAgent/LoopAgent and internal
MCP compatibility aliases in this pinned version. The patterns match the requested
tutorials and pass the local suite. Plan a tested migration before a dependency upgrade.

The intentionally defective review fixture's unittest run should fail. That is separate
from the 24 passing repository tests, which assert those defects are correctly reported.
