# Log Investigation Recipes

Read-only SQL templates for task outcomes, repeated failures, node exits, and version comparisons. Replace placeholders only after confirming UTC times and the live schema. Every statement here is read-only.

Invoke them through the skill's runner, naming the target explicitly:

```bash
python3 scripts/query.py --target <target> --timeout 120 --format json "<SQL>"
```

## Establish the Live Encoding

Before classifying outcomes, inspect the values actually present:

```sql
SELECT
  log_type,
  log_type_name,
  count(*) AS row_count,
  count_if(exception_code != 0) AS rows_with_exception
FROM {schema}.query_history
WHERE event_date BETWEEN '<start-date>' AND '<end-date>'
  AND event_time >= '<start-utc>'
  AND event_time < '<end-utc>'
GROUP BY log_type, log_type_name
ORDER BY log_type;
```

Also sample `user_agent` before choosing a task-name extraction expression.

## Count Successful, Failed, and Incomplete Executions

Classify one row per query first, then count. Adapt the terminal names to the encoding you found, and keep every terminal type in the classification: a type you did not expect must not fall into the incomplete bucket by default.

```sql
WITH per_query AS (
  SELECT
    query_id,
    any(user_agent) AS user_agent,
    count_if(log_type_name = 'Start') AS starts,
    count_if(log_type_name = 'Finish') AS finishes,
    count_if(log_type_name = 'Error' OR exception_code != 0) AS errors,
    count_if(log_type_name = 'Aborted') AS aborted
  FROM {schema}.query_history
  WHERE event_date BETWEEN '<start-date>' AND '<observation-end-date>'
    AND event_time >= '<start-utc>'
    AND event_time < '<observation-end-utc>'
    AND user_agent LIKE '%<target-warehouse-or-task>%'
  GROUP BY query_id
)
SELECT
  count_if(errors > 0) AS failed_executions,
  count_if(errors = 0 AND finishes > 0) AS successful_executions,
  count_if(aborted > 0) AS aborted_executions,
  count_if(starts > 0 AND finishes = 0 AND errors = 0 AND aborted = 0) AS incomplete_executions
FROM per_query;
```

`Aborted` is a real terminal state in at least one deployment, and it is often the interesting one during an incident: it is how a query that was cancelled or torn down ends, and it is distinct from both a SQL error and a query that is still running.

For a historical start window such as `[-2h, -1h)`, do not restrict every row to that same hour. Build the cohort of query IDs whose Start fell inside the requested window, then look for their terminal rows through now, the node exit, or another stated grace horizon. Otherwise a query that finished just after `-1h` is falsely labeled incomplete.

When asked how many tasks ran, say whether the number means executions or distinct extracted task names. For recurring tasks it is usually worth reporting both, then grouping failed and incomplete executions by task.

## Inspect Repeated Failures

For a bounded failed or incomplete cohort, group by SQL identity before reading every log:

```sql
SELECT
  query_hash,
  server_version,
  count(DISTINCT query_id) AS executions,
  count(DISTINCT exception_code) AS exception_codes,
  substring(any(exception_text), 1, 500) AS sample_exception
FROM {schema}.query_history
WHERE event_date BETWEEN '<start-date>' AND '<end-date>'
  AND query_id IN ('<query-id-1>', '<query-id-2>')
GROUP BY query_hash, server_version
ORDER BY executions DESC;
```

Then answer these independently:

- Are they the same `query_hash`, or merely the same task?
- Do the exception code and the normalized exception text agree?
- Did they run with comparable settings, data volume, version, and topology?
- Do their timelines converge on the same causal event, or only share a similar last sampled log line?

Do not compare per-query pipeline `NodeIndex(...)` values as if they were global processor identities.

## Investigate a Pod or Node Exit

Use a narrow UTC interval around `exitAt`:

```sql
SELECT
  timestamp,
  node_id,
  query_id,
  log_level,
  target,
  substring(message, 1, 1000) AS message
FROM {schema}.log_history
WHERE timestamp >= '<exit-minus-window-utc>'
  AND timestamp <= '<exit-plus-window-utc>'
  AND node_id = '<node-id>'
ORDER BY timestamp;
```

If the identifier you were given is a pod name rather than a `node_id`, first locate a small set of matching rows by the most selective warehouse or pod field and time window, then resolve the node ID from them.

Build the active-query cohort from Starts before the exit plus terminal records through the exit or a short, justified grace interval. Several unrelated query IDs disappearing together supports a node or process failure; it does not by itself explain why the node died.

For OOM analysis, look for a causal chain across node and container exit evidence, concurrent workload, memory limits and settings, allocation or spill behavior, periodic profiles, and the relevant source. The last watchdog sample is not a stack trace. A line such as `Slow async task detected` is periodic evidence of a slow poll; establish its baseline frequency in successful executions before assigning it significance.

## Find Who Shared the Node

A memory panic is a property of the node, so the failing query is rarely the whole story. List the heavy queries that overlapped it on the same cluster, then add up their per-node peaks:

```sql
SELECT
  query_id,
  log_type_name,
  query_duration_ms,
  scan_rows,
  to_string(peek_memory_usage) AS peak_per_node
FROM {schema}.query_history
WHERE event_date = '<incident-date>'
  AND cluster_id = '<cluster-id-from-the-failing-query>'
  AND event_time >= '<incident-utc-minus-window>'
  AND event_time < '<incident-utc-plus-window>'
  AND query_duration_ms > <threshold-ms>
ORDER BY query_duration_ms DESC
LIMIT 20;
```

Then pick the node ID that appears in the failing query's `peek_memory_usage` map and sum every peak reported for that same node. Two queries each below the per-query ceiling can still cross the node limit together.

**Extend the window past the incident.** A terminal row is written when a query ends, so a neighbour that was still running at the panic has no row yet. In one investigation the query that supplied the missing 144 GB finished 2m47s *after* the victim died: a window that stopped at the incident instant would have shown nothing and the analysis would have wrongly blamed the victim's own footprint.

Neighbours that never terminate in any window you can justify are still evidence — report them as unquantified rather than absent.

## Compare Versions or Rollback Phases

Build matched cohorts with the same `query_hash` and task, then label executions by version or time phase. Compare at least:

- outcome and observation completeness;
- `session_settings` and resource limits;
- scan rows and bytes, and duration;
- per-node memory rather than an unverified cross-node sum;
- spill and other operator statistics, accounting for sample timing;
- warning rate or duration, not just presence;
- the source paths that emit the relevant logs and update the relevant metrics.

Use the local source for every version under comparison to decide whether apparently similar log events represent comparable code paths. Treat a new code path as a candidate until successful controls, profiles, and resource evidence test the hypothesis.

## Dialect and Output Compatibility

- Keep `--target` explicit and confirm the org exposes the log schema; never substitute another org's history tables because a query returned nothing.
- Optimize the query before raising `--timeout` (whole seconds, default 600).
- Use explicit `AS` aliases. If `left(message, 500)` is parsed ambiguously, use `substring(message, 1, 500)`.
- Array length on a VARIANT is `array_length(...)`; `json_array_length` does not exist here.
- `session_settings` is a comma-separated `key=value` string, not JSON. Split on `,` then on the first `=`.
- Reading a VARIANT map: `to_string(col)` whole, or index one key. Truncating it with `substring` drops entries without warning.
- If a `VALUES` CTE is interpreted as a stage or rejected, use a bounded direct `IN (...)` list, or verify the supported dialect with a tiny read-only query first.
- Timestamps are UTC. Convert only for display, and say which zone you used.
