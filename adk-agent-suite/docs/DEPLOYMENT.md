# Deployment and operations

## Local API and database

1. Copy `.env.example` to `.env` and install from `uv.lock`.
2. Generate strong bearer tokens and map each to a customer/tenant in `API_TOKENS`.
   Empty configuration rejects access. The mapping is appropriate for a controlled
   demo or internal service; a public customer product should integrate its identity
   provider and token rotation/revocation, retaining the same trusted identity boundary.
3. Run `agent-suite init-db`. This creates an empty production schema and never seeds
   fictional demo inventory. Use a controlled catalog/issue import for your own data.
4. Start `agent-suite serve` and check `/healthz` and `/docs` on loopback.

For a demonstration, `agent-suite demo` creates a separate seeded database. Point
`DATABASE_PATH` at `artifacts/demo/demo.db` to explore it through the API. Keep
`AGENT_MODE=demo` until provider access and model quality are explicitly verified.

## Docker Compose

The supplied Dockerfile includes Python, pinned ADK dependencies, Node and the pinned
Gemini CLI. It runs as a non-root user. Compose adds PostgreSQL, named volumes,
read-only application files, temporary scratch space and capability restrictions.

```bash
cp .env.example .env
# Add a generated API_TOKENS mapping, provider secret, AGENT_MODE=live, and
# POSTGRES_PASSWORD with a strong random password to .env.
docker compose up --build
```

Compose initializes separate `suite` and `sessions` databases on a new volume.
Changing init SQL does not change an existing volume. Apply a reviewed migration for
existing databases. The simple `CREATE TABLE IF NOT EXISTS` initializer is for the
initial schema only; it is not a general migration engine.

Do not mount the Docker socket into the API. Cloud/container review workers should
use `REVIEW_TEST_MODE=skip` or a separately isolated execution service. The bundled
Docker test runner is meant for an operator-controlled workstation/CI host.

The Docker build and Compose runtime were not executed in the delivery environment.
Validate them in your own registry/runner before deploying. Pin base-image digests
and GitHub Action commit SHAs under your organization's supply-chain policy.

## Cloud Run

Prerequisites: a billed Google Cloud project, Artifact Registry, Cloud Run APIs,
Secret Manager, a runtime service account, networking to PostgreSQL/AlloyDB and
authorized Gemini access. Provision these in your own project; no cloud resources
were created by the supplied demo.

Example after building and pushing the image to your own registry:

```bash
gcloud run deploy adk-agent-suite \
  --image REGION-docker.pkg.dev/PROJECT/REPOSITORY/adk-agent-suite:1.0.0 \
  --region REGION --service-account RUNTIME_SERVICE_ACCOUNT \
  --no-allow-unauthenticated --port 8080 --cpu 2 --memory 2Gi \
  --concurrency 4 --max-instances 3 --timeout 240 \
  --set-env-vars AGENT_MODE=live,REVIEW_TEST_MODE=skip,SUITE_CONCURRENCY=4 \
  --set-secrets GOOGLE_API_KEY=gemini-key:latest,API_TOKENS=api-tokens:latest,DATABASE_URL=shop-dsn:latest,SESSION_DATABASE_URL=session-dsn:latest
```

Replace every uppercase placeholder; it is not a deploy-and-bill script. Add your
project's VPC connector or direct VPC egress configuration. Persistent domain and
session data must use PostgreSQL/AlloyDB, not Cloud Run's ephemeral filesystem.
Use a PostgreSQL SQLAlchemy async DSN such as `postgresql+psycopg://...` for sessions.
The synchronous domain adapter accepts `postgresql://...` with your TLS parameters.

For Vertex AI, configure `GOOGLE_GENAI_USE_VERTEXAI=true`, project and location, and
give the service account only the required model permissions. The external CLI wrapper
currently uses an API key, so Vertex-only shops should supply a dedicated CLI identity
adapter rather than assuming that an interactive developer OAuth login is inherited.

Cloud Run IAM and this app both use the Authorization header. If your ingress requires
an identity token while the application requires a bearer token, provide the IAM token
using `X-Serverless-Authorization` and keep the application's token in `Authorization`,
or place an authenticated gateway in front that resolves identity. Review your actual
ingress contract; do not disable authentication merely to make the demo work.

## AlloyDB and Toolbox

See `integrations/toolbox/README.md`. The shared schema uses PostgreSQL-compatible
types. Domain transactions lock rows and bind parameters. Toolbox only sees the
catalog table through a SELECT-only role. Remote MCP endpoints must be HTTPS except
for local loopback testing; ingress and database access are separate protections.
For production use short-lived service credentials, TLS, a private endpoint and
auditable role grants. PostgreSQL/AlloyDB operation and hosted MCP calls remain unverified
until you run the supplied tests and smoke checks against your own instance.

## Reliability, observability and data handling

- Overall invocation timeout: 180 seconds by default; maximum 24 ADK model calls.
  Research adds up to six grounded-search calls, each independently bounded. No order
  write is blindly retried. Clients can replay confirmation safely with the same key.
- Per-instance concurrency is bounded by a semaphore. Excess agent calls return 429.
  Place distributed quotas/rate limits at your gateway for a public service.
- `runtime.py` emits structured completion metadata: run ID, agent, mode, elapsed time,
  tool-event count and ADK token totals. Grounded-search calls use a separate GenAI client,
  so their token billing is not included in that ADK count. Use provider billing telemetry
  to account for the full cost. Demo zero-token metadata is explicitly synthetic.
- Sessions persist in ADK's database store. Saved trace artifacts may contain source
  snippets and business information. Set a retention period, access rules, encryption
  and deletion workflow appropriate to your deployment. Do not publish live customer traces.
- `/healthz` is a liveness endpoint, not an end-to-end dependency check. Add provider,
  database and MCP readiness checks at the deployment layer.
- The initial schema does not implement catalog import, tax/shipping calculation,
  discounts, payment capture, stock reservation, refunds or fulfillment. An order records
  confirmed unpaid intent. Commercial checkout needs those services, migrations, audit
  events/outbox handling and operational ownership before release.
- The code reviewer covers a small Python rule set and unittest projects. Expand rule
  coverage and isolated runner images for additional languages and dependency sets.
- Prompts discourage injection, but actual boundaries are tool allowlists, path controls,
  authentication, domain transactions and process isolation. Evaluate adversarial inputs
  with the specific model/version you choose.

## CI and release

GitHub Actions installs the frozen Python dependencies, checks formatting/lint, executes
the SQLite suite and all five demos, and uploads JSON/XML evidence. A second job tests
domain behavior on PostgreSQL 16. That job uses an expendable test database:
`TEST_DATABASE_URL` causes the test fixture to truncate the suite's tables between tests.
Never point it at a production database.

Before a real rollout, run the live smoke commands for all five agents with your model,
inspect citations and tool traces, exercise authorization with two tenants, run the
PostgreSQL job and measure load/cost on your chosen infrastructure. Record those results
in a new verification report rather than overwriting the supplied offline evidence.
