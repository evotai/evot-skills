# Incident investigation workflow

Read this before querying logs for an alert, OOM, node/process exit, incomplete query, recurring task failure, or version regression. Ordinary SQL and one-query performance analysis use [Query diagnostics](../diagnostics.md). All script paths below are relative to the installed skill root, not this reference directory.

## Read-only investigation

Use only SELECT, read-only CTEs, SHOW, and DESC. Do not create helper tables, mutate data, resize/restart compute, or rerun the failed workload to gather evidence. Cancelling existing workload queries is maintenance, not forensics. Only the helper's normal cleanup of its own evidence-reading query is permitted without a separate maintenance request.

Share the connection layer described in [Connection workflow](../connection.md) and [Organization selection](../organizations.md). Confirm origin, org, and warehouse before a request. Never display or hash credentials. Missing configuration requires private setup, not discovery of secrets in other tools.

## 1. Establish subject, log-serving org, and UTC window

Map an alert's fields before querying:

| Field | Meaning and use |
|-------|-----------------|
| `orgSlug`, `tenantID` | Monitored subject, not automatically the org serving shared logs. Check returned `tenant_id` against the subject when available. |
| `warehouse` | Warehouse running the workload. Narrow sampled `user_agent`; resolve cluster/node from the query's own row. |
| `taskID`, `taskName`, `rootRunID` | Scheduler identity for repeated executions of one task. |
| `queryID` | Anchor execution. Start here before searching broad message patterns. |
| `queryElapsed` | Seconds; compare with `query_duration_ms` to verify the execution. |
| `error` | Surfaced symptom, such as memory panic, UDF failure, or cancellation; not proof of the cause. |
| `time:` footer | Parse its explicit timezone. Original alert footers can be UTC, while chat-rendered times can be CST/UTC+8. |

A shared admin log org may contain a monitored tenant's events. If that is needed, ask the user to explicitly select/authorize its Organization ID and API origin; do not probe other orgs to find logs. Confirm the subject by query ID and tenant ID rather than substituting the log org's own tenant identity. If the confirmed org lacks logs, stop and report the missing access or incorrect log-serving org.

Write predicates in UTC. Convert a confirmed UTC+8 timestamp by subtracting eight hours, but do not shift a timestamp already marked UTC or `Z`. State both the user-facing incident time and the UTC scan window.

## 2. Verify schema before relying on telemetry

Use `SHOW DATABASES`, then DESC and small bounded samples in the confirmed org. Prefixes can be `log`, `logs`, or `system_history`; never switch tenants because a preferred prefix is absent. Read [Log schema](log-schema.md) before interpreting fields, log types, memory maps, or profile arrays.

Keep the serving warehouse distinct from the monitored workload's warehouse. Bound scans by date partition and precise timestamp where those columns exist. Pass the actual Organization ID and API origin explicitly:

```bash
python3 scripts/query.py --org <Organization-ID> --base-url <confirmed-api-origin> --timeout 120 --format json --max-rows 100 "<read-only-SQL>"
```

## 3. Anchor the execution and build a cohort

Read the known query's history first: node/cluster, duration, scan volume, exception, settings, version, and client/task metadata. Prefer aggregates, then drill into a bounded list of IDs. A missing row is a telemetry/access/window limitation, not proof that the execution never existed.

Read [Investigation recipes](query-recipes.md) for only the relevant procedure:

- successful/failed/aborted/incomplete execution counting;
- repeated failures grouped by query hash and task identity;
- pod/node exit and concurrent workload timelines;
- matched version or rollback comparisons.

Read [Memory incidents](memory.md) only for memory pressure, OOM, panic, or co-location questions. Read [Log export](log-export.md) only when an export is requested. Do not load all incident references for a simple query.

## 4. Evidence discipline

- Count executions by `query_id`, not history rows. Distinguish executions from distinct tasks.
- Inspect all observed terminal types. Aborted/cancelled is not automatically a SQL failure. Unexpected types must not fall into an incomplete bucket by default.
- Start without Finish is incomplete, not necessarily failed. Extend the observation horizon to find terminal rows after the requested start window. Sparse Start coverage prevents reliable incomplete counts; report it.
- Profiles/logs are sampled. Missing or zero spill/memory counters may mean not recorded. Do not attribute an operator from a last log line or a non-operator metrics blob.
- Pipeline indices are local to each execution, not shared global processor identities.
- A watchdog/slow-task line is an observation. Establish its baseline in successful executions before treating it as causal.
- Compare query identity, inputs, settings, duration, per-node memory, spill, topology, and server version. Map instrumentation to the code for each version; symbol names and statistic indices can change.
- Do not truncate VARIANT maps you intend to interpret. Use full JSON or extract individual keys. Narrow the query before raising timeout or output bounds.

For uncertain syntax, follow [SQL docs](../sql-syntax.md). The [API capability map](../api-capabilities.md) still applies during incidents: a personal token does not authenticate console history/profile REST APIs. Admin-only `QUERY_HISTORY` is another source in the same confirmed org, not a replacement for missing profiles or a reason to switch accounts.

## 5. Report what the evidence supports

State the confirmed origin/org and monitored subject, UTC window, cohort, query IDs, observed outcomes, telemetry gaps, and confidence. Separate observations, hypotheses, and recommended next checks. Keep competing explanations until ruled out. Call a finding the root cause only when log, profile/resource evidence, and the relevant code path support the same causal chain. Remediation is a separately authorized task, never an implicit investigation step.
