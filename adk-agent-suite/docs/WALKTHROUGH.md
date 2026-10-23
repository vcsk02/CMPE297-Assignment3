# Detailed code and execution walkthrough

## 1. Reproduce the submission

Open a terminal in the repository root. Run:

```bash
uv sync --frozen --extra dev --extra video
uv run --frozen --extra dev pytest -q
uv run --frozen agent-suite demo
```

Expected project result: **24 passed**. Dependency deprecation warnings may appear.
Expected demo result: five `mode=demo saved=...` lines. Open `artifacts/demo/index.json`,
then each named JSON file. These are actual saved runs. Random session, quote and
order IDs and elapsed times will differ between executions.

`agent-suite demo` deliberately uses separate demo/session databases under its output
directory. It clears those two demonstration databases on rerun. It cannot use a
configured production `DATABASE_URL` or remote catalog. The fixtures include fictional
companies, `.example` source links, a fictional store and three catalog products.

### Understand what is running

1. `cli.py` loads settings and chooses a scenario.
2. `runtime.py` constructs a fresh graph and `DatabaseSessionService`.
3. `agents.py` selects a scripted `BaseLlm` for demo mode or Gemini for live mode.
4. ADK Runner consumes model responses and executes actual function/MCP tools.
5. Each tool call and result is collected into the trace.
6. Deterministic domain/report checks run after generation.
7. Tools and sessions are closed, including MCP child processes.

The same graph runs in both modes. The demo model is a deterministic test adapter,
not an imitation of reasoning quality. It emits preselected function calls through
the ADK model interface, which lets us verify orchestration without a credential.
An arbitrary demo prompt does not produce new research; use `--mode live` for that.

## 2. Part a — deep research lead generation

Read `agents.py` (the `kind == "leads"` factory), `research.py`, `schemas.py`, and
the `lead_*` roles in `demo_model.py`.

The graph is a `SequentialAgent` containing a planning agent, a bounded `LoopAgent`,
and a typed report writer. The loop contains a research agent and a critic. The critic
can request a specific follow-up or call `finish_research`; that tool raises ADK's
escalation action to end the loop. Three loop iterations and six search calls are the
hard limits. ADK model calls also have a separate limit of 24 per invocation.

The planner extracts an industry and geography, then describes what historical
market-entry patterns to look for. The research agent searches for those patterns
and candidates that exhibit them. The critic asks whether identity, freshness and
source coverage are adequate. The writer returns a `LeadReport`, with market,
patterns, leads, observed signals, cited URLs, rationale and limitations.

`search_web` is an asynchronous ADK FunctionTool. In live mode it calls Gemini with
Google Search grounding, collects the provider's grounding source URLs, and stores
their provenance in ADK session state. It does not fetch arbitrary user-specified
URLs or execute web-page code. Queries and responses are bounded. The provider call
has its own timeout inside the overall invocation timeout.

`validate_lead_report` is outside the model. It parses the typed report, rejects a
citation absent from the retrieved source set, deduplicates official website domains,
and computes an explicit priority heuristic: 25 points per distinct signal plus
10 per cited source, capped at 100. This score is **not** a calibrated probability.
URL membership does not prove every semantic assertion or website identity; the
report says human verification is required. Live grounding can return redirect URLs,
so the writer must preserve those exact retrieved citation URLs.

### Execute and inspect

```bash
uv run agent-suite demo
python -c "import json; d=json.load(open('artifacts/demo/leads.json')); print(json.dumps(d['output'],indent=2))"
```

In `trace`, find two `search_web` calls and one `finish_research` call. The first
search records two fictional companies; the second checks a hiring signal. The
final report contains three source records, Northstar with a score of 70 and Meridian
with a score of 60. The `.example` URLs explicitly mark these as fixtures.

For live research, set `GOOGLE_API_KEY`, select your supported `GEMINI_MODEL`, then:

```bash
uv run agent-suite run leads --mode live --identity local_operator \
  --prompt "Find three fintech companies showing credible Thailand expansion signals. Distinguish facts from predictions." \
  --output artifacts/live-leads.json
```

Inspect actual citations, publication freshness, facts versus inferences, and omissions.
Do not use fixture scores as model-quality evaluation. Do not assume a company wants
outreach merely because a public expansion signal exists. The implementation neither
harvests private contact information nor sends messages.

## 3. Part b — Gemini CLI inside an ADK pipeline

Read `cli_tool.py`, `paths.py`, `process.py`, `fixture_cli.py`, and the `cli` graph.

The pipeline has a planner, a worker with `gemini_cli(task, relative_path)`, and a
synthesizer. This is an actual ADK FunctionTool calling an external executable.
The task and relative path remain separate arguments; no shell command is assembled.

Before starting the process, `source_snapshot` rejects absolute paths, `..`, symlinks,
unsupported files, hidden directories, large files and oversized snapshots. It drops
`.env`, git metadata, `GEMINI.md`, `AGENTS.md`, virtual environments and dependencies.
At most 100 files and 200 KB are copied into a temporary workspace. This limits the
scope of what the external CLI can analyze and avoids letting repository configuration
silently activate hooks or additional MCP integrations.

The live invocation is equivalent to:

```bash
gemini --prompt "...bounded task..." --output-format json \
  --approval-mode plan --model YOUR_SUPPORTED_MODEL
```

The wrapper creates an isolated CLI home with a read-tool allowlist, excluded write,
shell and network tools, no inherited user MCP configuration, and a minimal environment.
It passes only the provider credential needed by the CLI. It never uses YOLO mode.
These are tool-policy limits, not an operating-system sandbox. For untrusted multi-tenant
hosting, run each live CLI invocation inside a separate container with read-only mounts,
resource limits and restricted egress; do not treat prompt instructions as isolation.

`run_process` streams stdout/stderr under a byte cap instead of collecting unlimited
output. It enforces a timeout and kills the whole POSIX process group on completion,
timeout or cancellation. The tool rejects nonzero status and malformed JSON. Raw
provider stderr is not returned to the model. On Windows, prefer WSL2 for this path.

### Execute and inspect

The offline demo still launches a real Python subprocess. `fixture_cli.py` parses the
copied Python files with AST and returns function names and a fixed test plan. It is
labeled `backend=fixture_subprocess` in `artifacts/demo/cli.json`.

For live CLI execution:

```bash
cd integrations/gemini-cli
npm ci --ignore-scripts
./node_modules/.bin/gemini --version
cd ../..
export GEMINI_CLI_BINARY="$PWD/integrations/gemini-cli/node_modules/.bin/gemini"
uv run agent-suite run cli --mode live --identity local_operator --target review_target \
  --prompt "Explain the integer-start DFS failure and propose a focused regression suite" \
  --output artifacts/live-cli.json
```

The pinned Gemini CLI version is 0.65.0. Its installation, version and help flags were
checked. No authenticated Gemini CLI inference is claimed in the supplied evidence.

## 4. Part c — MCP bug-assistance agent

Read `mcp_server.py`, `bugs.py`, and the `bugs` branch of `agents.py`.

The ADK client constructs `McpToolset` with `StdioConnectionParams`. It launches
`python -m agent_suite.mcp_server bugs`, performs MCP discovery, and exposes only:

| Tool | Behavior |
|---|---|
| `search_issues` | Tenant-scoped literal matching of existing issues |
| `get_issue` | Reads a specific issue only in the authenticated tenant |
| `search_knowledge` | Retrieves troubleshooting articles with KB identifiers |
| `propose_issue` | Persists a draft for later review |

The server is a real `FastMCP` server using JSON-RPC over stdio. Stdout is reserved
for the protocol. The trusted parent supplies database location and tenant identity
through the child environment. There is **no tenant argument** in the tools that a
model could modify to access another user's issue.

The workflow searches for duplicate tickets before proposing a new one. The seeded
`BUG-101` matches the duplicate-checkout scenario. The agent reads that issue, retrieves
`KB-001`, and returns reproduction steps and an idempotency hypothesis. The hypothesis
is a diagnostic lead, not a claim to have inspected an actual production incident.

### Execute and inspect

```bash
python -c "import json; d=json.load(open('artifacts/demo/bugs.json')); print(json.dumps(d['trace'],indent=2))"
```

You should see `search_issues`, `get_issue`, and `search_knowledge` MCP calls and
their actual responses. There is no unnecessary duplicate draft.

To demonstrate a new ticket in live mode, initialize your local tracker database and
ask for a genuinely new issue. The tool can save a draft, but it cannot finalize it.
Review the returned title/body and draft ID. A trusted operator can then run:

```bash
uv run agent-suite confirm-bug DRAFT_ID --identity YOUR_TENANT
```

The equivalent authenticated API route is `POST /v1/bugs/{draft_id}/confirm`.
Confirmation is tenant-scoped and replay-safe. It writes to the bundled local issue
tracker. This code does not claim to publish GitHub issues. To integrate an external
tracker later, implement its adapter behind the same ownership and confirmation boundary.

## 5. Part d — production-oriented code review

Read `review.py`, the `review` graph, and `examples/review_target/`.

`ParallelAgent` runs three custom `BaseAgent` checks. Each writes a separate state
key, avoiding overlapping parallel updates:

| Check | Evidence | Safety boundary |
|---|---|---|
| AST | Syntax errors, dynamic execution, shell=True, interpolated SQL, stack/pop heuristic | Parses source; never imports it |
| Ruff | Real linter JSON and exit status | `--isolated` ignores repository lint configuration |
| Tests | Real unittest stdout, stderr and exit status | Default skip; explicit trusted or Docker mode |

The LLM explains these results with a typed `ReviewNarrative`. `final_review` builds
the actual verdict from deterministic findings and test status. The model cannot
discard a high-severity finding by writing a reassuring summary. A clean small rule
set yields `needs_human_review`, never an automatic approval or merge.

The intentionally broken fixture initializes `stack = start`. Integer starts fail
because integers have no `.pop()`; zero starts return before searching. It also has
SQL interpolation and an arbitrary shell call. Its three tests therefore produce
one pass, one failure and one error. The assistant preserves this evidence.

### Execute and inspect

```bash
uv run agent-suite demo
python -c "import json; d=json.load(open('artifacts/demo/review.json')); print(json.dumps(d['output'],indent=2))"
```

Expect `changes_requested`, three AST findings, and `test_execution.status=failed`.
The project pytest suite explicitly asserts that these problems are found.

For another project, place it under the configured `WORKSPACE_ROOT` and select a
relative directory. The default `REVIEW_TEST_MODE=skip` avoids executing untrusted
code. To run tests in an isolated Docker container, first pull `python:3.12-slim`,
set `REVIEW_TEST_MODE=docker`, and run:

```bash
uv run agent-suite run review --mode live --identity local_operator --target your_project \
  --prompt "Review correctness, security, and regression coverage" --output artifacts/review.json
```

The Docker test command disables networking, mounts source read-only, drops capabilities,
uses a non-root UID, restricts memory/CPU/processes, and allows only temporary scratch
space. The provided target command uses unittest and the standard Python image, so
third-party project dependencies need a separately built, audited runner image.
Hosted environments without Docker must delegate execution to an isolated job service.
`trusted` mode is reserved for code the operator explicitly trusts; it is not a sandbox.

## 6. Part e — transactional e-commerce agent

Read `commerce.py`, `storage.py`, the shop MCP tools, `api.py`, and
`integrations/toolbox/README.md`.

The shopping model has tools to search products, find stores, prepare a quote and
read an order. All catalog values come from the database, and money is integer USD
cents. The model cannot finalize purchases. A prepared quote stores the product,
quantity, unit price, customer and a ten-minute expiration.

The trusted confirmation route derives customer identity from bearer authentication.
In one transaction it checks the idempotency key, locks the quote, checks ownership,
checks existing order, expiration, current product price and stock, decrements stock,
and inserts exactly one unpaid order. Unique constraints enforce one order per quote
and one order per customer/key. SQLite uses `BEGIN IMMEDIATE`; PostgreSQL uses row
locks with `FOR UPDATE`. Concurrent buyers of the last item cannot both succeed.

Price changes fail closed and require a new quote. A quote itself does not reserve
stock. Retrying a completed confirmation returns the same order, even if the quote
has since expired. Reusing a key for a different quote is rejected. Delivery changes
require the current version, preventing one client from silently overwriting another.

### Execute and inspect

```bash
uv run agent-suite demo
python -c "import json; print(json.dumps(json.load(open('artifacts/demo/shop_checkout.json')),indent=2))"
```

The shopping MCP calls return the $129 Trail Runner Pro, a fictional San Jose store,
and a quote. The **trusted demo driver**, outside the model, confirms it and repeats
the exact request to demonstrate the same order ID. Orders have
`status=confirmed_unpaid`; this project does not capture payment or dispatch shipments.

### HTTP walkthrough

In `.env`, set `DATABASE_PATH=artifacts/demo/demo.db` and a generated `API_TOKENS`
mapping with identity `demo_customer`. Start `agent-suite serve`. In a separate terminal,
set `SUITE_TOKEN` to your generated token, then:

```bash
curl http://127.0.0.1:8080/healthz
curl -X POST http://127.0.0.1:8080/v1/agents/shop \
  -H "Authorization: Bearer $SUITE_TOKEN" -H 'Content-Type: application/json' \
  -d '{"prompt":"Find running shoes under $150 and prepare a quote for one pair"}'
# Copy the returned output.quote.quote_id after reviewing price and quantity.
curl -X POST http://127.0.0.1:8080/v1/orders/QUOTE_ID/confirm \
  -H "Authorization: Bearer $SUITE_TOKEN" -H 'Idempotency-Key: checkout-example-001'
# Repeat the exact request: the order ID must stay the same.
curl http://127.0.0.1:8080/v1/orders/ORDER_ID -H "Authorization: Bearer $SUITE_TOKEN"
```

PowerShell users can use the interactive `/docs` page or `Invoke-RestMethod`.
Supplying a different `customer` field in the request is rejected by the schema.
The model never receives a `confirm_order` tool. Authorization is code, not merely
an instruction to behave responsibly.

### AlloyDB / MCP Toolbox variant

Use `DATABASE_URL` for the PostgreSQL-compatible database, a persistent
`SESSION_DATABASE_URL` for ADK sessions, and a private/read-only Toolbox catalog.
`CATALOG_MCP_URL` enables `catalog_search` over Streamable HTTP; the other tools remain
on the bundled MCP server. `integrations/toolbox/tools.yaml` exposes a parameterized
catalog SELECT only. The checkout service still owns the atomic transaction.
See the integration guide for setup and the deployment guide for hosted prerequisites.

## 7. Verification and limitations

`tests/test_agents.py` exercises all five graphs with real tools. `test_commerce.py`
checks retries, ownership, expiry, price changes, invalid quantities, stock races and
delivery versions. `test_boundaries.py` checks path escape, symlinks, source filtering,
timeouts, output limits, invented citations, issue confirmation and HTTP authentication.

The SQLite suite passed locally. The PostgreSQL CI job is provided but has not run in
this environment, where a non-root PostgreSQL server could not be started. Live model
quality, hosted services, resource sizing and latency under production traffic remain
deployment-specific work. The dependency version is pinned; ADK 2.12 emits deprecation
warnings for the tutorial-style workflow classes, so evaluate migration before upgrading.

## 8. Record, publish and submit

The narrated video uses actual source snippets and captured execution evidence.
Regenerate it with `make video` on a machine with FFmpeg's `flite` filter. Follow
`docs/PUBLISHING.md` to push source, artifacts, video, subtitles and chapter metadata
to GitHub, then upload to your authorized YouTube channel. Include the returned repo
URL and actual uploaded video URL in your submission. Never substitute example links.
