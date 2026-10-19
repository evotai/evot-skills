# Bounded raw and readable log exports

Load only when the user requests a log export. Follow the [incident workflow](index.md) for the serving org, API origin, subject, permissions, and UTC windows. All script paths here are relative to the installed skill root. Log files may contain sensitive user data; follow the user's storage/sharing policy and never export unrelated tenants' rows.

When no format is specified, keep the raw schema-first JSON Lines and also offer one-event-per-line output. `jq` is optional and needed only for the readable formatter. If missing, keep the raw export and explain that readable formatting is unavailable; ordinary SQL/API work must still proceed. Do not install tools without permission.

## Query exact columns in order

The formatter indexes fields positionally. Preserve this exact column order and replace placeholders with confirmed values. Add an explicit SQL limit and split the time window when necessary:

```sql
SELECT timestamp, path, target, log_level, cluster_id, node_id,
       warehouse_id, query_id, message, fields, batch_number
FROM {schema}.log_history
WHERE timestamp >= '<start-utc>' AND timestamp < '<end-utc>'
  AND node_id = '<node-id>'
ORDER BY timestamp
LIMIT <bounded-row-count>
```

```bash
python3 scripts/query.py --org <Organization-ID> --base-url <confirmed-api-origin> --format json \
  --max-rows <bounded-row-count> "<read-only-SQL>" > raw.jsonl
```

Check the command's exit status and stderr before calling an export successful. A query helper cap, SQL limit, or short window can make the output incomplete. Report the bound and coverage; narrow/split windows or use a stable continuation strategy for a larger requested export. Do not present a capped file as complete evidence. Prefer unique output filenames so a second export does not silently replace earlier evidence.

## Readable output, when jq is available

```bash
jq -r -f scripts/format_log_history.jq raw.jsonl > events.log
```

The formatter:

- consumes the query helper's schema-first JSON Lines and drops only the schema line;
- emits every data row, including a row without a timestamp;
- converts UTC timestamps to Asia/Singapore (UTC+8), retaining milliseconds;
- escapes embedded newlines/tabs so one event occupies one physical line;
- writes no ANSI color.

Each line has this shape:

```text
YYYY-MM-DD HH:mm:ss.SSS LEVEL [0] LEVEL - <query-id-or-> - <message> | target=... node_id=... warehouse_id=... path=... cluster_id=... batch_number=... fields=...
```

An absent timestamp is printed as `-`. State that the readable file is UTC+8 while raw predicates/timestamps remain UTC. If the user requires another display timezone, do not falsely label this fixed-offset formatter as configurable; retain raw UTC or explicitly implement and verify an alternative.

Report file paths, row counts, selected API origin/org and monitored subject, UTC coverage, display timezone, and any truncation or telemetry gaps. Never include credentials in filenames, files, or output.
