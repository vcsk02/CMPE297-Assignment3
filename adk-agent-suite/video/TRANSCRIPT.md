# Narrated walkthrough transcript

## 00:00 — Five agents. One runnable repository.

This walkthrough builds five agents with Google's Agent Development Kit. We will inspect the implementation, run the supplied scenarios, and explain the evidence each agent produces. The projects cover lead research, Gemini command line delegation, MCP bug assistance, code review, and e-commerce. The important distinction throughout is what actually executed. The offline model is a clearly labeled scripted adapter. The ADK runner, MCP protocol, databases, subprocesses, and code checks execute for real. Live Gemini inference and cloud deployment require your own credentials and are not claimed here.

## 00:37 — Start with a reproducible environment

Start in the repository root with Python three point twelve and uv installed. The first command installs the frozen dependencies, including the development and video extras. The next command runs the project test suite. The demo command then runs all five agents and writes reports into the artifacts directory. It uses separate demo databases, so it cannot change a configured production store. No Gemini key is needed for these scenarios. On Windows, the same uv commands work. The readme also provides a PowerShell virtual environment alternative.

## 01:09 — The runtime uses the actual ADK Runner

The runtime is shared by all five projects. It builds a fresh graph, creates a database-backed session, and assigns a new run identifier. The initial state includes the configured source target and research evidence containers. Runner dot run async drives the agent graph with a maximum of twenty four model calls. The runtime captures function calls, function responses, messages, and token metadata. At the end, it validates the domain output and closes the MCP toolsets and session store. This common runner makes the saved traces useful for debugging and demonstrations.

## 01:43 — A: Plan, investigate, critique, report

Part A is the deep research agent for lead generation. Its planner extracts the target market and industry and proposes a research strategy. A researcher and critic then iterate inside a bounded loop. The researcher gathers public expansion signals; the critic checks identity, freshness, and source coverage. If evidence is insufficient, the critic asks for a focused follow-up. Once the evidence is adequate, the finish research tool ends the loop. A separate writer produces the typed lead report. Three iterations and six searches are hard limits, so the agent cannot research indefinitely.

## 02:18 — Grounded search preserves provenance

The search web function is an ADK tool. In live mode, it calls Gemini with Google Search grounding enabled. It extracts the returned source URLs and keeps them in session state with the answer. In demo mode, the same tool stores explicitly fictional company evidence. The first query discovers two candidate companies. The second query checks a hiring signal with another source. Research queries, result sizes, search count, and provider time are bounded. The tool does not execute web content or fetch arbitrary URLs supplied by the model.

## 02:51 — Validate citations after generation

The report is checked outside the model. Pydantic validates the shape, and every cited URL must belong to the retrieved evidence set. Leads are deduplicated by website domain. Priority is computed with a transparent rule: twenty five points per distinct signal and ten points per source, capped at one hundred. This is a ranking heuristic, not a probability of purchase. Citation membership also does not prove that every statement is true. The output therefore requires human verification, especially for company identity, freshness, and any business inference.

## 03:24 — Lead research: inspect the real output

Here is the captured lead report from the demo run. Northstar has local hiring and partnership signals, backed by two fictional source URLs. Meridian has hiring and market pilot signals with one source. The complete JSON includes the actual tool trace, the three stored source records, and the model mode. The trace contains two search calls followed by finish research. To research actual businesses, set your provider credential and run the leads command in live mode with your own prompt. Then verify the resulting sources before using the report.

## 03:57 — B: Delegate to Gemini CLI as a tool

Part B is the advanced tool agent. It is a sequential ADK pipeline with a planner, a worker, and a final synthesizer. The worker exposes an asynchronous function named Gemini CLI. The model passes a task and a relative directory to this function. The function prepares a bounded source snapshot, runs an external command, and returns structured results. The synthesizer explains those actual results without claiming that files were changed. In offline mode the executable is a Python fixture double. In live mode it is the pinned Google Gemini CLI.

## 04:31 — Constrain the source snapshot

Before delegation, the path utility makes the directory relative to an operator-owned root. Absolute paths and parent traversal are rejected. Symlinks are rejected as well. The snapshot copies supported source files only, with a maximum of one hundred files and two hundred kilobytes. Hidden configuration, environment files, git metadata, dependencies, and repository agent instruction files are excluded. This prevents repository configuration from silently becoming CLI authority. It is still important to treat the remaining source as untrusted data and to isolate live execution when serving untrusted customers.

## 05:10 — Run the external CLI with explicit limits

The process runner takes an argument list directly, so a task string cannot become shell syntax. It reads standard output and standard error incrementally under a byte limit. It applies a timeout and terminates the process group during cleanup, including cancellation. The live wrapper uses JSON output and plan approval mode. It creates an isolated CLI home, allows read tools, excludes write and shell tools, and passes a minimal environment. These are useful policy controls, but they are not an operating system sandbox. A public multi-tenant service should add isolated containers.

## 05:45 — CLI execution: identify the backend honestly

The captured tool response shows which files the subprocess analyzed and which functions its AST parser found. Its backend is explicitly fixture subprocess. The test plan includes an integer-start DFS regression, repeated checkout keys, and nonnegative stock. For real Gemini CLI use, install the pinned package with npm, set Gemini CLI binary to that executable, provide your API key, and run the CLI agent in live mode. Version zero point sixty five point zero and its headless flags were checked. An authenticated inference result is not part of this offline evidence.

## 06:19 — C: A real MCP bug-assistance server

Part C uses the Model Context Protocol. The ADK client launches a Fast MCP stdio server as a child process. It discovers and exposes only four bug tools: search issues, get issue, search knowledge, and propose issue. The authenticated tenant identity comes from the trusted parent process environment. It is absent from tool arguments, so the model cannot switch to another tenant. The server reserves standard output for JSON RPC and sends logs to standard error. This is a real protocol connection rather than direct Python function calls disguised as MCP.

## 06:55 — Triage duplicates before creating work

In the scenario, checkout retries create duplicate orders. The assistant first searches existing issues and finds bug one hundred one. It reads the issue and searches the knowledge base for idempotency guidance. Its response describes how to reproduce the retry, compare order identifiers, and verify stock. The diagnosis remains a hypothesis to investigate. Because a matching ticket exists, this run does not create a duplicate draft. The saved JSON includes each MCP request and response, making it possible to show exactly which evidence the assistant used.

## 07:29 — New issues stop at a reviewable draft

When a new issue is needed, propose issue validates title and body length and stores a draft. The model has no confirmation tool. A separate authenticated API route or trusted local command confirms that exact draft. Confirmation checks tenant ownership and is replay-safe. The bundled tracker is local; it does not claim to publish GitHub issues. This separation is useful because creating a draft is reviewable, while publishing changes shared work. The tests verify that one tenant cannot confirm or read another tenant's draft or issue.

## 08:01 — D: Code review starts with deterministic evidence

Part D is the code review assistant. Its parallel stage runs three custom ADK agents. The AST check finds syntax errors and selected risky patterns without importing the code. Ruff runs as a real linter with isolated configuration. The test stage is skipped by default unless the operator explicitly selects trusted or Docker mode. Each check writes a separate session key. Only after those checks finish does the model explain the results. The final verdict is computed in code, so a reassuring model summary cannot erase a deterministic finding.

## 08:34 — Inspect the intentionally broken fixture

The demonstration project intentionally contains three defects. The DFS function assigns start directly to stack, then calls pop. An integer start therefore fails, and a zero start exits too early. The fixture also interpolates a customer name into SQL and exposes shell true. The three regression tests produce one pass, one failure, and one error. These failures are expected evidence for the reviewer. They are different from the repository's own pytest checks, which pass because they assert that the assistant correctly reports these problems.

## 09:06 — Keep unsafe execution outside the default path

The review execution boundary matters. Static checks parse or lint a source snapshot, while tests execute code. The default mode skips tests. Docker mode runs a non-root process without networking, with a read-only source mount, dropped capabilities, and limits on memory, CPU, and process count. The image supplied here supports standard-library unittest projects; applications with dependencies need an audited runner image. Trusted mode is used only for this known demonstration fixture. Hosted environments without Docker should delegate test execution to an isolated job service.

## 09:41 — Review output preserves failures and findings

The saved review report contains the model explanation, all deterministic findings, and the actual unittest output and exit code. The verdict is changes requested because the AST findings and failing tests require action. If this limited rule set found nothing, the result would still require human review. It never automatically approves or merges a pull request. To extend the project, add focused rules and language-specific isolated runner images, then verify that model changes cannot hide deterministic evidence.

## 10:12 — E: Shopping tools prepare; the caller confirms

Part E is the e-commerce assistant. Its tools search catalog products, find stores, prepare a quote, and read order status. Product prices and stock come from the database, and money is represented in integer U S dollar cents. In this scenario, the agent finds running shoes under one hundred fifty dollars and prepares a quote for one pair. It cannot place an order or capture a payment. Confirmation is an authenticated caller action outside the model's tool list, and customer identity is fixed by the server.

## 10:43 — An expiring quote is not a stock reservation

Prepare order validates the requested quantity and current product availability. It creates a quote containing the product identifier, customer, quantity, unit price, and a ten minute expiration. The returned response explicitly says that no order has been placed. A quote does not reserve stock. If another customer buys the last item, confirmation must fail cleanly. Similarly, if the product price changes before confirmation, a new quote is required. These checks are enforced by the domain service rather than left to the shopping model's judgment.

## 11:17 — One transaction enforces checkout invariants

Confirm order begins one database transaction. It checks whether the customer and idempotency key already identify a completed order. It then locks the quote, verifies ownership, and checks whether the quote already has an order. Before writing, it checks expiration, current price, and stock. Stock decrement and order creation commit together. SQLite uses an immediate transaction, while the PostgreSQL adapter uses row locks. Unique constraints reinforce one order per quote and one order per customer and key. The model does not have access to this confirmation method.

## 11:52 — Checkout replay returns the same unpaid order

The captured checkout artifact shows the quote and resulting unpaid order. The trusted demo driver confirms it, then repeats the same request. Both responses refer to the same order identifier, and stock is decremented once. The project also tests eight concurrent buyers competing for the last item, with exactly one successful confirmation. These are local SQLite results. No payment was captured and no shipment was dispatched. A commercial deployment still needs payment, tax, fulfillment, migrations, audit events, and its own operational validation.

## 12:27 — Authenticate identities outside model arguments

The API maps strong bearer tokens to trusted customer identities. Empty configuration rejects protected requests. The caller cannot set a different customer in the request body, and the shopping MCP server does not expose a customer argument. Quote confirmation requires an idempotency header. Order reads and delivery changes also check ownership, and delivery changes require the current version. Agent calls have an overall timeout and a bounded concurrency limit. The supplied API tests exercise missing authentication, cross-customer requests, and invalid identity fields.

## 13:03 — Optional AlloyDB and MCP Toolbox catalog

For the database-backed cloud variant, the domain adapter accepts a PostgreSQL or AlloyDB connection string. An optional catalog MCP URL enables a read-only Toolbox search tool over Streamable HTTP. The YAML file exposes a parameterized catalog select and no order mutation tools. Transactional writes remain in the application service. The deployment guide covers private networking, persistent sessions, service credentials, and Cloud Run. These hosted paths are supplied as deployment assets and have not been provisioned or verified in this environment.

## 13:38 — Verification: examine the captured run index

The run index lists all five completed scenarios and their actual tool-call counts. The project suite contains twenty four passing tests. It checks each ADK graph, MCP interactions, authorization, citation membership, path restrictions, subprocess timeout and output limits, order replay, price changes, expiration, delivery versions, and concurrent stock. The complete execution log and JUnit report are committed as evidence. The PostgreSQL CI job is provided separately but has not run here. Scripted demo success verifies orchestration and invariants, not live model quality.

## 14:16 — Move from demonstration to a live evaluation

To evaluate live behavior, configure your provider key and supported Gemini model, initialize your own database, and run the commands in the walkthrough. Start with read-only tasks and inspect source citations and tool results. The CLI path additionally needs the installed external executable. For deployment, use persistent PostgreSQL sessions and inventory, authenticated ingress, and isolated execution workers. The repository pins tested dependency versions and documents current deprecation warnings. Treat model quality, cost, latency, hosted database behavior, and deployment limits as measurements to verify in your own environment.

## 14:57 — Publish the actual repository and video

The repository includes the finished MP4, captions, transcript, chapter timestamps, and detailed guides. The GitHub publishing script creates a private repository by default using your authenticated GitHub CLI session. The YouTube helper uses your local OAuth consent and verifies the intended channel before uploading. It records the actual returned video URL. This delivery does not invent GitHub or YouTube links, and publication requires authorized account access. After upload succeeds, add the real video URL to the readme and submit both links. Every command and boundary discussed here is documented beside the code.
