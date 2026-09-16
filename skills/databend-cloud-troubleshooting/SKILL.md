---
name: databend-cloud-troubleshooting
description: Diagnose Databend Cloud incidents from its logs, starting from an alert card or a query_id. Use when a Databend alert needs root-cause analysis, when a query failed, hung, or never finished, when a warehouse or node OOMed, restarted, or exited, when a task keeps failing, or when one query's behaviour changed between versions or after a rollback. Triggers include "analyze the databend logs", "why did this OOM", "node crashed", "which tasks failed", "incomplete queries", "root cause", "troubleshoot this alert", "export log_history", 以及中文的「看下这条告警」「排查这条告警」「分析问题原因」「定位根因」「为什么 OOM」「内存超限」「任务失败」「节点挂了」「查一下根因」「日志导出」. For running arbitrary SQL or reading query profiles outside an incident, use the databend-cloud skill instead.
license: Apache-2.0
compatibility: Requires python3 and network access to api.databend.com; readable log exports also need jq
metadata:
  evot:
    requires:
      env: [BENDCLOUD_DSN]
      bins: [python3, jq]
    envHints:
      BENDCLOUD_DSN: bendcloud://<org>:<api-token>@api.databend.com/<warehouse>
---

# Databend Cloud Incident Analysis

Read-only log forensics: work out why a query failed, ran slow, or never finished, why a warehouse or node OOMed or exited, or why behaviour changed between versions.

This skill is scoped to investigations. To run arbitrary SQL, read a query profile, or query a tenant that is not under investigation, use the `databend-cloud` skill instead — same API, same credentials, no incident discipline.

## Read-only, always

Investigation is not maintenance. Run only `SELECT`, read-only CTEs, `SHOW`, and `DESC`. Never create helper tables, insert, or mutate anything, not even to make an analysis easier. Never print, hash, or echo credentials.

## Connect

One variable per org, injected by evot into every bash command:

```
/env set BENDCLOUD_DSN=bendcloud://<org>:<api-token>@api.databend.com/<warehouse>
/env set BENDCLOUD_DSN_<NAME>=bendcloud://<org>:<api-token>@api.databend.com/<warehouse>
```

Pass `--target <name>` to choose a named org. Name the target explicitly for every log investigation and confirm it exposes the log schema before drawing any conclusion:

```bash
python3 scripts/query.py --target <name> "SHOW DATABASES"
```

If the log schema is missing there, report a connection-context failure and stop. Do not substitute another org, and do not fall back to another tenant's history tables: a conclusion drawn from the wrong tenant is worse than no conclusion.

If the script exits with a configuration error, relay its `/env set` line to the user verbatim and stop. Never guess credentials or read them from other files.

## Start from an alert card

Most investigations start from an alert card, not a query_id. Map its fields before querying anything:

| Card field | What it is | Use it for |
|---|---|---|
| `orgSlug`, `tenantID` | the **monitored** tenant | the subject, and the `tenant_id` you expect to see in log rows |
| `warehouse` | the warehouse that ran it | narrowing `user_agent`; resolve `cluster_id` from the query's own row |
| `taskID`, `taskName`, `rootRunID` | the scheduler's identity | grouping repeated failures of one task |
| `queryID` | the failing execution | the anchor for everything below |
| `queryElapsed` | seconds | cross-check against `query_duration_ms` to confirm you have the right row |
| `error` | surfaced error | the code to explain (1104 memory panic, 2607 UDF, 1043 canceled by client) |
| `time:` footer | UTC | the incident instant |

Two traps that will silently ruin an analysis:

- **The alert's org is not where its logs live.** A card names the monitored tenant; the log tables usually sit in a separate admin org. List the targets you have, pick the one that exposes the log schema, then prove you are in the right place: rows for the card's `queryID` must carry the same `tenant_id` as the card. Never analyze a tenant you did not confirm.
- **Chat-rendered card times are local (CST, UTC+8); the log tables are UTC.** Subtract 8 hours before writing any predicate. A 17:42 alert is `09:42` in `event_time` and `timestamp`.

Anchor on `queryID` first. One row of `query_history` gives node, cluster, duration, scan volume, exception, version, and `user_agent` — enough to plan every later step.

## Schema prefix is not fixed

Log tables live under a log database (`log`, or `logs`) in some deployments and under `system_history` in others. Confirm before querying, and sample a few rows before encoding assumptions about `log_type`, `user_agent`, or profile statistics. `{schema}` below stands for the confirmed prefix.

Read [references/log-schema.md](references/log-schema.md) before selecting fields or interpreting profiles, and [references/query-recipes.md](references/query-recipes.md) for the execution-counting, repeated-failure, node-exit, and version-comparison procedures.

## Run a query

```bash
python3 scripts/query.py --target <name> --format json "<SQL>"
```

Flags: `--target`, `--warehouse`, `--timeout` (whole seconds, default 600), `--format table|json`. Timestamps are UTC; convert only for display and say which zone you used.

Prefer small aggregate queries, then drill into a bounded list of query IDs. Select substrings of large messages instead of dumping whole `query_text`, `session_settings`, or `profiles`. If a query times out, reduce its scan and its output before raising `--timeout`.

Never truncate a VARIANT map you intend to read. `substring(to_string(peek_memory_usage), 1, 120)` silently cuts entries off and hides the node that mattered — select the whole value, or extract one key at a time.

## Memory panics need a node-level answer

A message like `memory usage 192.0 GiB(...) exceeds limit 192.0 GiB(...)` is the **process** tracker, not a per-query ceiling. The query named in the alert may simply be the one that awaited the task that panicked, so never stop at it. Work the ladder:

1. Read both ceilings from `session_settings` (a comma-separated `key=value` string, not JSON): `max_memory_usage` is the node limit, `max_query_memory_usage` the per-query one. Compare them with the number in the panic.
2. Read the query's own `peek_memory_usage` — a `{node: bytes}` map, so it tells you the footprint per node rather than a total.
3. If the query sits below its own ceiling, the node was shared. Find the co-tenants and add up their per-node peaks — see the co-location recipe in [references/query-recipes.md](references/query-recipes.md). A query under its limit can still be the victim of a neighbour under its limit.
4. Check whether the protection ladder actually engaged: `query_out_of_memory_behavior`, the `*_spilling_memory_ratio` settings, `max_hash_join_spill_level`, `max_aggregate_spill_level`, and the `*_spilled_bytes` counters. All-zero spill counters next to a memory panic mean the ladder never fired — report that as a finding, not as proof of why.

## Rules of engagement

- Name the target and confirm its schema, every time. Never substitute another org because a query returned nothing.
- Count executions by `query_id`, not by history rows, and say whether a number means executions or distinct tasks.
- A Start with no Finish is incomplete, not failed. Look past the requested window for the terminal row before concluding that a query never ended.
- Classify every terminal type you observe, including ones you did not expect. A type you did not plan for must not land in the incomplete bucket by default.
- A watchdog or slow-task message is an observation, not a cause. Establish its baseline rate in successful executions first.
- Profiles and logs are sampled. Absent or zero spill and memory values may mean "not recorded yet", not "did not happen".
- Per-query pipeline indices are local to that execution. Never treat them as shared processor identities.
- Use `query_hash` to find comparable executions, and compare settings, input size, duration, memory, spill, and version before attributing anything to code.
- Keep source-derived details current: map log text and instrumentation against the source for each version compared, instead of assuming symbol names are stable.

## Export log_history as a readable .log

When the user asks to pull `log_history` without naming a format, keep the raw export and also write a one-event-per-line file. Select the columns in this exact order, because [scripts/format_log_history.jq](scripts/format_log_history.jq) indexes them positionally:

```sql
SELECT timestamp, path, target, log_level, cluster_id, node_id,
       warehouse_id, query_id, message, fields, batch_number
FROM {schema}.log_history
WHERE timestamp >= '<start-utc>' AND timestamp < '<end-utc>'
  AND node_id = '<node-id>'
ORDER BY timestamp
```

```bash
python3 scripts/query.py --target <name> --format json "<SQL>" > raw.jsonl
jq -r -f scripts/format_log_history.jq raw.jsonl > events.log
```

Each line reads `YYYY-MM-DD HH:mm:ss.SSS LEVEL [0] LEVEL - <query-id-or-> - <message> | target=... node_id=... ...`, in Asia/Singapore time (UTC+8), with embedded newlines and tabs escaped so one event stays on one physical line. No row is dropped, and an event without a timestamp prints `-` in that column. Do not add ANSI colour to the file.

## Report evidence, not vibes

State the comparison cohort, the observation horizon, and which telemetry was missing. Keep what the logs show separate from what you infer from it. Name competing explanations while they are still alive. Call something a root cause only when logs, profile or resource evidence, and the corresponding code path all support the same causal chain.
