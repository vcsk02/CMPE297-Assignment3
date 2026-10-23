# Optional MCP Toolbox catalog on PostgreSQL / AlloyDB

The default shopping demo uses the real bundled MCP stdio server and SQLite.
For the AlloyDB variant, use the same application schema with a PostgreSQL DSN,
and expose catalog reads through MCP Toolbox. Inventory writes remain in
`Shop.confirm_order`, where ownership, price checks and stock updates form one transaction.
This prevents an LLM from composing separate unsafe checkout SQL operations.

The configuration uses the current Toolbox flat YAML resource format. It is an
integration template: hosted Toolbox and AlloyDB were not provisioned in this delivery.

1. Provision a private AlloyDB PostgreSQL database using your Google Cloud project.
   Connect over private networking or the official AlloyDB Auth Proxy. Use TLS for a
   direct remote connection. Store the DSN and credentials in Secret Manager.
2. Set `DATABASE_URL` and run `agent-suite init-db`. Load your actual catalog through
   an operator-controlled import, not through the model. Do not run demo seeding.
3. Create a dedicated catalog database user, grant `CONNECT` and schema `USAGE`,
   and grant `SELECT` on `products` only. Do not grant access to orders or customers.
4. Set `PGHOST`, `PGPORT`, `PGDATABASE`, `PGUSER`, `PGPASSWORD` for this read-only role.
5. Install and pin MCP Toolbox 1.14.0 using the official release or
   `npx @toolbox-sdk/server@1.14.0 --config integrations/toolbox/tools.yaml` for local evaluation.
   Consult its `--help` for bind/address flags. Serve only to your private network.
6. Set `CATALOG_MCP_URL` to its authenticated Streamable HTTP endpoint
   (normally `/mcp`), and `CATALOG_MCP_TOKEN` if the ingress requires a bearer token.
7. Run `agent-suite run shop --mode live --identity your-customer --prompt "Find running shoes under $150"`.
   The agent now discovers only `catalog_search` from Toolbox and the remaining
   shopping tools from the bundled server. Confirm that the trace calls that tool.

Do not expose an unauthenticated Toolbox to the internet. Use a service identity,
authenticated ingress, a read-only database account and an egress policy. An IAM
proxy may need to mint short-lived identity tokens instead of a static token.

References: [Toolbox repository](https://github.com/googleapis/mcp-toolbox),
[Toolbox CLI](https://mcp-toolbox.dev/reference/cli/), and the
[provided AlloyDB codelab](https://codelabs.developers.google.com/codelabs/sports-agent-adk-mcp-alloydb).
