# ADK Agent Suite — five end-to-end agents

An original implementation of all five requested Google ADK agent projects, with
working tools, API endpoints, persistence, automated checks and a narrated walkthrough.
The supplied tutorials are credited in [REFERENCES.md](docs/REFERENCES.md).

| Part | Agent | Implemented workflow | Entry point |
|---|---|---|---|
| a | Deep research lead generation | Plan → bounded search/critique loop → cited, validated lead report | `agent-suite run leads` |
| b | Gemini CLI tool agent | Plan → external CLI FunctionTool → synthesis | `agent-suite run cli` |
| c | MCP bug assistant | Discover MCP tools → duplicate search → issue/KB lookup → triage or draft | `agent-suite run bugs` |
| d | Code review assistant | Parallel AST, Ruff, test execution → narrative → deterministic verdict | `agent-suite run review` |
| e | E-commerce assistant | MCP catalog/store lookup → quote → authenticated transactional confirmation | `agent-suite run shop` |

**Verification:** all five run through the actual ADK Runner in offline demo mode.
The 24 project tests pass. MCP stdio, SQLite, AST inspection, Ruff, subprocess execution,
order confirmation and concurrent-stock checks execute for real. Demo model replies and
web results are scripted fixtures. Gemini inference, hosted services, Docker builds,
AlloyDB/Toolbox deployment and external publication have **not** been verified here.
This is a production-oriented reference implementation, not a claim of a deployed or
commercially certified service. See [verification status](docs/VERIFICATION.md).

## Start in two commands

Use Python 3.12 or 3.13 and [uv](https://docs.astral.sh/uv/). From this directory:

```bash
uv sync --frozen --extra dev --extra video
uv run --frozen agent-suite demo
```

No Gemini key is needed for the demo. It writes JSON reports and complete tool traces
to `artifacts/demo/`. The review fixture is deliberately flawed; its failing unittest
run is an expected review finding, while the **project** pytest suite must pass.

For Windows PowerShell, the same `uv` commands work. Without uv:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python -m pip install -e ".[dev,video]"
.\.venv\Scripts\agent-suite demo
.\.venv\Scripts\python -m pytest -q
```

`pip install -e` uses the pinned direct versions but does not enforce the complete uv
transitive lock. Use uv for reproducible installs.

## Watch and follow the walkthrough

- [Watch the complete code and execution walkthrough on YouTube](https://youtu.be/Wk8a2sJSKU8)
- [Narrated MP4](video/adk-agent-suite-walkthrough.mp4) — actual code and captured demo outputs,
  with synthetic narration; no live Gemini inference is implied.
- [Subtitles](video/walkthrough.srt), [chapter timestamps](video/CHAPTERS.md), and
  [full transcript](video/TRANSCRIPT.md).
- [Detailed code and execution walkthrough](docs/WALKTHROUGH.md).
- [YouTube publication instructions](docs/PUBLISHING.md).

The MP4 and upload helper are provided. No YouTube URL exists until an authorized
channel upload succeeds. The upload helper records the resulting URL instead of
inventing a video link.

## Live Gemini mode

```bash
cp .env.example .env
# Set GOOGLE_API_KEY in .env, and select a supported GEMINI_MODEL.
uv run agent-suite init-db
uv run agent-suite run leads --mode live --identity local_operator \
  --prompt "Find three Thailand fintech expansion leads with source-backed signals"
```

The default `gemini-flash-latest` is configurable. Pin a supported model version for
your deployment and evaluate it on your tasks. Live calls incur your provider's charges.
The CLI integration additionally needs Node 20+ and the pinned external CLI:

```bash
cd integrations/gemini-cli
npm ci --ignore-scripts
cd ../..
export GEMINI_CLI_BINARY="$PWD/integrations/gemini-cli/node_modules/.bin/gemini"
uv run agent-suite run cli --mode live --target review_target --identity local_operator \
  --prompt "Explain the DFS bug and suggest regression tests"
```

PowerShell:

```powershell
$env:GEMINI_CLI_BINARY = "$PWD/integrations/gemini-cli/node_modules/.bin/gemini.cmd"
```

On Windows, Node `.cmd` launch behavior differs from POSIX. Prefer WSL2 for live CLI
delegation and Docker review isolation. The offline demo is portable Python.

## Run the API

Set `API_TOKENS` to a JSON map of strong bearer tokens to customer IDs. Empty
configuration rejects all protected routes. Identity comes from this mapping,
not an LLM argument or request body.

```bash
# Generate a token locally; do not commit it.
python -c "import secrets; print(secrets.token_urlsafe(32))"
# Edit .env: API_TOKENS={"YOUR_GENERATED_TOKEN":"demo_customer"}
# To use the demo catalog, set DATABASE_PATH=artifacts/demo/demo.db in .env.
uv run agent-suite serve
```

Open `http://127.0.0.1:8080/docs`, click **Authorize**, and enter the token.
`POST /v1/agents/shop` with a purchase request prepares a quote.
Only `POST /v1/orders/{quote_id}/confirm` with an `Idempotency-Key` places an
unpaid order. An LLM cannot call this endpoint through its tools.

## Tests, deployment and files

```bash
uv run --frozen --extra dev pytest -q --junitxml=artifacts/test-results.xml
uv run --frozen ruff check src tests scripts
uv run --frozen ruff format --check src tests scripts
```

GitHub Actions defines SQLite end-to-end checks and a PostgreSQL transaction test job.
The workflow has been supplied; no remote Actions run is claimed. [Deployment guide](docs/DEPLOYMENT.md)
covers Docker Compose, Cloud Run, PostgreSQL/AlloyDB, sessions and observability.

| Path | Contents |
|---|---|
| `src/agent_suite/agents.py` | All five ADK graphs and MCP connections |
| `src/agent_suite/demo_model.py` | Explicit scripted BaseLlm adapter |
| `src/agent_suite/research.py` | Grounded search and report validation |
| `src/agent_suite/cli_tool.py` | Gemini CLI subprocess tool |
| `src/agent_suite/mcp_server.py` | Real bug/shop MCP tools |
| `src/agent_suite/review.py` | AST, Ruff, tests, deterministic verdict |
| `src/agent_suite/commerce.py` | Quote/order invariants and transactions |
| `src/agent_suite/api.py` | Authenticated agent and confirmation endpoints |
| `tests/` | End-to-end, authorization, concurrency and failure checks |
| `artifacts/` | Actual demo outputs and project test evidence |
| `docs/` | Detailed walkthrough, deployment, references, publishing |
| `video/` | Narrated walkthrough, captions and chapter metadata |
| `integrations/toolbox/` | Optional MCP Toolbox/AlloyDB catalog configuration |

To publish everything to your GitHub account, use
`bash scripts/publish_github.sh adk-agent-suite --private`, or on Windows,
`./scripts/publish_github.ps1`. Add `--public` / `-Public` only if you want a public
submission. See [publishing guide](docs/PUBLISHING.md) for the YouTube upload.
