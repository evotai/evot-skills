---
name: databend-cloud
description: Query and diagnose Databend Cloud. Use when the user wants to run SQL on Databend Cloud, investigate a query_id, read query_history / profile_history / log_history, find slow or failed queries, or compare the same query's performance across time. Triggers include "query databend", "check query logs", "look up query_id", "debug this query", "show query profile", "run SQL on bendcloud".
license: Apache-2.0
compatibility: Requires python3 and network access to api.databend.com
metadata:
  evot:
    requires:
      env: [BENDCLOUD_DSN]
      bins: [python3]
    envHints:
      BENDCLOUD_DSN: bendcloud://<org>:<api-token>@api.databend.com/<warehouse>
---

# Databend Cloud

Run SQL and diagnose queries through the Databend Cloud REST API.

## Setup

One variable holds everything. evot persists it and injects it into every bash command:

```
/env set BENDCLOUD_DSN=bendcloud://<org>:<api-token>@api.databend.com/<warehouse>
```

`<warehouse>` defaults to `default`. For several orgs, set `BENDCLOUD_DSN_<NAME>` per org and pass `--target <name>`.

If the script exits with a configuration error, relay its `/env set` line to the user verbatim and stop. Never guess credentials or read them from other files.

## Run SQL

```bash
python3 scripts/query.py "<SQL>"
python3 scripts/query.py --target acme --format json "<SQL>"
```

Flags: `--target` picks an org, `--warehouse` overrides the DSN warehouse, `--timeout` (default 600s), `--format table|json`.

`table` is the default and best for reading. `json` emits the column schema on line 1 and one row per line after it — use it when exact values matter.

Timestamps returned by Databend Cloud are UTC.

## Schema prefix is not fixed

System tables live under `system_history` in some environments and `logs` in others. Confirm before querying:

```sql
SHOW DATABASES
```

For current table definitions and diagnostic guidance, fetch <https://docs.databend.com/guides/diagnose.md>. It documents every column of `query_history`, `profile_history`, `log_history`, `access_history`, and `login_history`.

`{schema}` below stands for the confirmed prefix.

## Diagnose a query_id

Default to the last 3 days unless the user gives a range. `query_history` filters on `event_time`; `profile_history` and `log_history` filter on `timestamp`. Always order by the time column so output reads chronologically.

Step 1 — execution summary:

```sql
SELECT query_text, query_kind, sql_user, query_start_time, query_duration_ms,
       query_queued_duration_ms, scan_rows, scan_bytes, result_rows, result_bytes,
       written_rows, written_bytes, exception_code, exception_text,
       join_spilled_bytes, agg_spilled_bytes,
       bytes_from_remote_disk, bytes_from_local_disk, bytes_from_memory,
       peek_memory_usage, server_version, handler_type
FROM {schema}.query_history
WHERE query_id = '<QUERY_ID>'
  AND event_time BETWEEN now() - INTERVAL 3 DAY AND now()
ORDER BY event_time
```

Step 2 — operator breakdown:

```sql
SELECT * FROM {schema}.profile_history
WHERE query_id = '<QUERY_ID>'
  AND timestamp BETWEEN now() - INTERVAL 3 DAY AND now()
ORDER BY timestamp
```

Step 3 — server logs, when the first two are inconclusive:

```sql
SELECT timestamp, log_level, target, message, fields
FROM {schema}.log_history
WHERE query_id = '<QUERY_ID>'
  AND timestamp BETWEEN now() - INTERVAL 3 DAY AND now()
ORDER BY timestamp
```

## What to look at

1. Failure: `exception_code` and `exception_text`.
2. Work done: `scan_rows` against `result_rows` — a large gap means weak pruning or filtering.
3. Queueing: high `query_queued_duration_ms` is resource contention, not query cost.
4. IO tiers: `bytes_from_memory` / `bytes_from_local_disk` / `bytes_from_remote_disk`.
5. Spilling: non-zero `join_spilled_bytes` or `agg_spilled_bytes` means memory pressure.
6. Profile: parse the `profiles` JSON for the slowest operator.
7. Logs: ERROR and WARN lines around the query window.

## Compare the same query over time

`query_parameterized_hash` identifies one logical query regardless of literal values. Read the hash for a known `query_id`, then pull every execution sharing it and compare `query_duration_ms`, scan and IO metrics, spill metrics, and `server_version` to locate a regression.

`user_agent` usually carries the task and warehouse name, which is useful for narrowing to one workload.

## Ad-hoc examples

```sql
SELECT query_id, query_text, exception_text, event_time
FROM {schema}.query_history
WHERE exception_code != 0
  AND event_time BETWEEN now() - INTERVAL 3 DAY AND now()
ORDER BY event_time DESC
LIMIT 20
```

```sql
SELECT query_id, query_text, query_duration_ms, scan_rows
FROM {schema}.query_history
WHERE query_duration_ms > 10000
  AND event_time BETWEEN now() - INTERVAL 3 DAY AND now()
ORDER BY query_duration_ms DESC
LIMIT 20
```
