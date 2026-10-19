# Warehouse management and history through the Query API

These are Cloud gateway SQL extensions, submitted with a personal token to the existing `POST /v1/query`. They are **not** new personal-token REST management endpoints. Use the confirmed API origin and explicit `--org <Organization-ID>`. The account's effective gateway roles must include `account_admin` for every statement in this reference, including read-only listing/history. A non-admin token may run ordinary SELECT but still be denied here.

Start with read-only discovery. Obtain explicit approval before create, resize, resume, suspend, rename, drop, or settings/tag changes. Explain the target and expected cost/disruption. Never execute this entire page as a setup script, automatically resume a warehouse after an unrelated error, or re-submit a mutation on timeout.

## List warehouses

```bash
python3 scripts/query.py --org <Organization-ID> --base-url <confirmed-api-origin> "SHOW WAREHOUSES"
python3 scripts/query.py --org <Organization-ID> --base-url <confirmed-api-origin> "SHOW WAREHOUSES LIKE '%prod%'"
```

Typical columns include `name`, `state`, `size`, auto-suspend/auto-resume, cluster counts, role, comment, tags, creator, and creation time. Advanced columns depend on tenant features. Inspect the actual schema rather than assuming every deployment returns the same fields.

Warehouse listing does not discover the user's organizations. Do not use it to change the already confirmed site or org. A permission error does not mean no warehouses exist.

## Create a warehouse

After user approval, for example:

```sql
CREATE WAREHOUSE IF NOT EXISTS 'etl-wh'
    WITH warehouse_size = Small
         auto_suspend = 600
         initially_suspended = TRUE
         auto_resume = TRUE
         comment = 'Approved ETL warehouse';
```

`initially_suspended = TRUE` avoids immediate startup; later queries may resume it because `auto_resume` is true. Creating compute resources can affect billing and quotas even when no data is changed. `IF NOT EXISTS` avoids changing an existing resource; it does not prove its settings match the requested configuration.

Warehouse names are validated at runtime: 3–63 ASCII letters/digits/hyphens; leading `~` names are reserved. Quote names containing hyphens. Use actual supported sizes from the deployment/catalog rather than guessing. Standard examples use `Small`; defaults and available sizes can vary by deployment.

The gateway also recognizes `REPLACE WAREHOUSE`, but replacement can recreate resources and is not a safe default. Prefer explicit create or targeted alter with user approval.

## Resume, suspend, resize, and configure

The following are separate examples requiring their own authorization:

```sql
ALTER WAREHOUSE 'etl-wh' RESUME;
ALTER WAREHOUSE 'etl-wh' SUSPEND;
ALTER WAREHOUSE 'etl-wh' SET warehouse_size = Medium;
ALTER WAREHOUSE 'etl-wh' SET auto_suspend = 600 auto_resume = TRUE;
ALTER WAREHOUSE 'etl-wh' SET TAG environment = 'production', owner = 'data-team';
ALTER WAREHOUSE 'etl-wh' UNSET TAG owner;
```

- `RESUME` can start billing; `SUSPEND` can disrupt active work. Do not call either just to troubleshoot an authentication failure.
- `ALTER ... SET` options are whitespace-separated, not a comma-separated generic SQL option list. Tag assignments have their own comma syntax.
- `AUTO_SUSPEND = 0` or `NULL` disables automatic suspend and can increase cost; nonzero values must meet the runtime minimum. Do not reset options the user did not ask to change.
- Role changes affect access. Confirm grants/roles with the user, and do not broaden access automatically.
- Advanced version, architecture, cache/spill, and short-suspend options require tenant feature gates. Do not expose or set internal-only options to bypass a restriction. Consult the official SQL reference and actual deployment before using them.

Verify the resulting state/configuration with `SHOW WAREHOUSES` using the same origin and org. Configuration propagation and warehouse transitions can be asynchronous; do not claim readiness from a successful mutation alone.

## Rename or drop

```sql
ALTER WAREHOUSE 'etl-wh' RENAME TO 'etl-next';
DROP WAREHOUSE IF EXISTS 'etl-wh';
```

Rename requires the source to be suspended. The implementation creates a replacement warehouse and deletes the old resource; explain that this is not a cosmetic metadata update. Do not suspend first without approval. After a confirmed rename, report the new name; use it in subsequent authorized `--warehouse` arguments rather than the old name.

Drop removes a compute resource and can interrupt workloads. `IF EXISTS` does not make the operation read-only. Never remove a `default` warehouse as part of credential setup.

## Session selection

```sql
USE WAREHOUSE 'etl-wh';
```

This validates a warehouse and returns a session setting. Independent `query.py` calls do not retain that session. Use `--warehouse etl-wh` on each request instead of relying on a persistent session.

## Bounded query history

The actual gateway parser supports `QUERY_HISTORY`, not a guessed `SHOW QUERY HISTORY` statement:

```sql
QUERY_HISTORY BY WAREHOUSE 'etl-wh' LIMIT 50;
```

For a user-confirmed UTC window, replace the placeholders before executing:

```sql
QUERY_HISTORY BY WAREHOUSE 'etl-wh'
    FROM '<UTC-start: YYYY-MM-DD HH:MM:SS>'
    TO '<UTC-end: YYYY-MM-DD HH:MM:SS>'
    LIMIT 100;
```

The clause order is warehouse, FROM, TO, LIMIT. Warehouse and time clauses are optional. Without a window, the current implementation defaults to the last hour; the default limit is `10`. Use explicit narrow windows and bounds for investigations. Time values are UTC unless explicitly qualified.

Data comes from the gateway's query-details history stream, not from a persistent result page. This does not replace every field in `system_history`/`logs`, guarantee profiles, or expose another org's logs. For SQL history schemas and profile analysis, follow [Diagnostics](diagnostics.md). Treat missing telemetry as a limitation, not evidence that a query never ran.

## Gateway-local result lifecycle

Management SQL executes in the gateway. The response carries `X-Databend-Query-Source: gateway`, a query ID for correlation, and completed schema/data (possibly zero rows). It does not create an ordinary query-node result handle.

The helper recognizes the HTTP source header, reports the result, and does not issue query-node status/page/kill/final requests for this local execution. This avoids spurious errors or waking compute after a completed control-plane operation. Do not infer this mode from SQL text or an untrusted JSON field.

An old deployment without this source metadata may behave differently. Do not blindly repeat a management mutation to obtain a query ID or clearer response; verify resource state using the same API origin and org.

## References and provenance

Use [SQL syntax and docs](sql-syntax.md) for the official warehouse SQL reference. Source checks used the platform's `docs/warehouse-management-sql.md`, gateway management grammar/tests, `gateway/proxy/proxy.go`, `gateway/proxy/warehouse.go`, and `gateway/pkg/auth/identity.go`. The runtime admin gate is authoritative even when generic SQL documentation describes broader privileges for another deployment.
