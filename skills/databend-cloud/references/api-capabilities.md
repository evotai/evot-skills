# Personal-token API capability map

Use this map before selecting a Cloud API. It was checked against the local Cloud platform and webapi source, not by probing production with a user's token. A route's existence, Swagger tag, or use of the word "token" does not establish personal-token authentication. Deployment versions can differ; report an observed mismatch instead of trying another host or credential type.

## Credential types

The key configured by this skill is the console-created **personal API token**, including current `dbc_` tokens and previously issued tokens without that prefix. It is account-linked; each request validates the account's active organization membership and derives its role.

Do not confuse it with a console access/refresh JWT, an audience-bound OAuth token, a SQL user password, a Kubernetes service-account token, or an internal service credential. Putting a personal token in `Authorization: Bearer` does not turn it into a console JWT.

## Direct personal-token surface

Use the confirmed API origin, explicit `--org <Organization-ID>`, and warehouse. See [Query API](query-api.md) for headers, bodies, responses, and lifecycle examples.

| Method | Path | Purpose | Side effects |
|--------|------|---------|--------------|
| `POST` | `/v1/query` | Execute SQL, including supported gateway management SQL. | Depends on the statement; can mutate data, permissions, or compute resources. |
| `GET` | `/v1/query/{queryID}` | Inspect a known query's execution status. | Does not submit SQL. |
| `GET` | `/v1/query/{queryID}/page/{pageNum}` | Fetch one server-issued result page. | Advances result consumption; not a persistent history/export API. |
| `GET` | `/v1/query/{queryID}/final` | Release result resources. | Can make remaining results unavailable. |
| `POST` | `/v1/query/{queryID}/kill` | Cancel an authorized running query. | Interrupts execution; is not a guaranteed rollback of committed work. |

Only this route group installs `TryAPITokenExchange` followed by `AuthRequired`. The conversion happens inside the server for that request; it is not a login/token-exchange API that returns a reusable console session to the caller.

## More capabilities through SQL, not new REST endpoints

The same `POST /v1/query` supports:

- Database and table discovery, schema inspection, SELECT, DML, DDL, stages, and supported task statements, subject to SQL privileges and deployed features. Check exact syntax through [SQL documentation](sql-syntax.md).
- Gateway management SQL: warehouse listing, create, alter/resume/suspend/rename, drop, warehouse session selection, and bounded query-history lookup. See [Warehouse management SQL](warehouse-management.md).

The current gateway checks `account_admin` for **all** recognized management statements, including `SHOW WAREHOUSES` and `QUERY_HISTORY`. Do not infer admin privileges from possession of a personal token. Resource changes can start compute, incur cost, disrupt queries, or remove a warehouse. Require explicit user approval.

Management SQL is not proof that the similarly named console REST endpoint accepts personal tokens. Gateway-local responses also do not have an ordinary query-node paging/finalization lifecycle.

## Public catalogs: no personal token needed

The API ingress exposes `/api/v1`; these two routes have no authentication middleware in the reviewed source. Call them on the already selected API origin **without** a key, cookies, or Authorization header. They describe service catalogs, not the user's tenant resources or permissions.

| Method | Path | Parameters | Response |
|--------|------|------------|----------|
| `GET` | `/api/v1/cloud-providers` | None. | `{ "success": true, "data": [...] }`; provider name, on-shelf status, regions and readiness/catalog metadata. |
| `GET` | `/api/v1/warehouse-sizes` | Optional `provider` and `region` query parameters. Use values from the provider catalog. | `{ "success": true, "data": [...] }`; name/value, vCPUs, compute units, credit cost/currency. |

HTTP templates, with the selected origin supplied separately:

```http
GET /api/v1/cloud-providers
Accept: application/json
```

```http
GET /api/v1/warehouse-sizes?provider=<provider>&region=<region>
Accept: application/json
```

Do not treat catalog pricing as an account invoice, billing balance, entitlement, or a promise that a particular tenant can use a size/region. Do not send the personal key to public metadata requests just because one is configured. A backend `/healthz` route exists, but the reviewed API-domain ingress does not expose it; do not advertise it as a public tenant endpoint.

## Console/session-only routes: not personal-token calls

The following source routes use console authentication without personal-token conversion. This table is a boundary reference, not instructions to obtain or scrape a console session.

| Capability | Example source route | Personal-token alternative |
|------------|----------------------|----------------------------|
| Current account / organization discovery | `GET /api/v1/account/info`, `GET /api/v1/my/orgs` | Ask for Organization ID and pass `--org`; server memberships are not discovered automatically. |
| Tenant and connection information | `GET /api/v1/orgs/{orgSlug}/tenant`, `.../tenant/connect-info` | Use the confirmed API origin, org, and warehouse; do not retrieve SQL passwords from another API. |
| Warehouse REST operations | `/api/v1/orgs/{orgSlug}/tenant/warehouses` and its warehouse-specific operations | Supported management SQL through `/v1/query`, with `account_admin` and explicit approval for changes. |
| History lists, counts, details, and profiles | `/api/v1/query/orgs/{orgSlug}/query-history/...` | Bounded SQL against authorized history schemas, or `QUERY_HISTORY` for eligible admin accounts. |
| CSV/Excel result download | `GET /api/v1/orgs/{orgSlug}/query/{queryID}/download`, `.../download-excel` | Fetch authorized query pages; report output caps. This is not equivalent to the console's saved-result export. |
| Streaming load / stage upload | `PUT /v1/streaming_load`, `PUT /v1/upload_to_stage` | These exact routes have only `AuthRequired`, despite their `/v1` prefix. Use documented SQL loading workflows where available; do not attach a personal token and assume they work. |
| Account token management | `/api/v2/apitoken/{tokens,create,drop,status}` | Create/revoke personal tokens manually in the console. Personal-token possession does not authenticate this v2 proxy. |
| Pipelines, taskflows, provisioning, and alert APIs | Other `/api/v1/...` and `/api/v2/...` business routes | Use documented SQL features when available; otherwise report that this skill has no verified personal-token API for the operation. |
| MCP and internal exchange endpoints | `/mcp`; internal token-exchange routes | Different credential contracts. Do not send the personal token, impersonate a workload, or scrape browser cookies. |

In particular, `X-DATABENDCLOUD-ORG` cannot compensate for an endpoint that does not accept a personal token, and the Query API does not return an authenticated console session in response headers/cookies for reuse.

## Source evidence for maintainers

Paths below are relative to the respective source repositories, not files required at skill runtime:

- Platform: `cloud/charts/frontend/templates/ingress.yaml` and `cloud/stacks/frontend/values.yaml.tmpl` establish API-domain routing and site hosts.
- Webapi: `controllers/query/query_controller.go` establishes the five personal-token routes; `controllers/auth/auth.go` and `pkg/http/header.go` establish token conversion and headers.
- Webapi: `controllers/org/{org_controller,tenant_controller}.go`, `controllers/common/load_controller.go`, and `controllers/query/proxy_v2_controller.go` establish session-only routes and public catalogs.
- Webapi: `controllers/mcp/mcp_controller.go` and `controllers/internalapi/databend_token_exchange_controller.go` establish separate OAuth/workload credentials.
- Platform: `gateway/proxy/proxy.go`, `gateway/pkg/auth/identity.go`, `gateway/proxy/{warehouse,management_query}.go`, and `docs/warehouse-management-sql.md` establish management SQL, the admin gate, and gateway-local responses.

Do not broaden this allowlist solely from generated Swagger or frontend request wrappers. Recheck the route, middleware chain, service authorization, and public ingress together before adding an API.
