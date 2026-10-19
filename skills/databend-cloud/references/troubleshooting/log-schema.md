# Databend Cloud Log Schema Notes

Practical fields observed in Databend Cloud log tables. Use `DESC` and a small sample to confirm the live schema: deployments differ, and instrumentation changes between versions.

`{schema}` stands for the confirmed prefix. One shared Cloud log tenant exposed these tables as `log` and had no `system_history` table at all; other deployments expose them under `system_history`. Confirm with `SHOW DATABASES` and sample a few rows before writing an analysis.

## `{schema}.query_history`

Useful fields include:

- `event_date`, `event_time`, `query_start_time`, `query_duration_ms`
- `tenant_id`, `node_id`, `query_id`
- `user_agent`, `query_text`, `query_hash`
- `log_type`, `log_type_name`
- `exception_code`, `exception_text`
- `server_version`, `has_profile`
- `scan_rows`, `scan_bytes`, `peek_memory_usage`
- `session_settings`

In one observed deployment, the live encoding was `log_type = 1` Start, `2` Finish, `3` Error, `4` Aborted. Do not universalize these numeric values: inspect `log_type_name`, the exception fields, and the distinct live values first. A failure may be represented by a terminal type, a nonzero exception, or both, and one sample window can be too short to reveal every terminal type that exists.

**Start rows can be almost absent.** In that same deployment a 105-minute window held 46 Start rows against 532,799 Finish rows, and a query that ran for 33 minutes had no Start row at all — only its Error row. Count the two types before relying on either. Where Start coverage is this sparse, terminal rows are the only trustworthy signal: "has a Start but no Finish" will not find incomplete work, and a missing Start proves nothing about whether a query ran. Say so in the report instead of presenting an incomplete count as zero.

`Aborted` with `exception_code = 1043` (`canceled by client`) is a cancellation, commonly the scheduler giving up or retrying. Do not fold it into failures without saying who cancelled it.

`user_agent` may contain client metadata followed by tenant, task, and warehouse components. Sample it before extracting a task name. Avoid assuming a fixed array offset. If task names have a reliable marker, a targeted expression such as `regexp_substr(user_agent, 'task_[^:]+')` is safer than an unchecked split; otherwise keep the full value until its format is established.

`peek_memory_usage` is a `{node_id: bytes}` map, not a scalar or a cluster total. Start rows often contain zero. In the observed deployment it carries **that query's own footprint per node**, not the node's total: two queries whose maps shared a node reported 144,091,684,934 and 75,067,833,589 for it, which cannot both be node-wide at overlapping times. Treat that reading as inferred, not documented. Prefer per-node values, and when you do sum across nodes say that you did.

`session_settings` is a comma-separated `key=value` string, not JSON. For memory incidents the keys that matter are `max_memory_usage` (node limit), `max_query_memory_usage` (per-query limit), `query_out_of_memory_behavior`, `allow_query_exceeded_limit`, the `*_spilling_memory_ratio` family, and the spill level caps `max_hash_join_spill_level` and `max_aggregate_spill_level`. Read them from the failing query's own row rather than assuming cluster defaults.

## `{schema}.log_history`

Useful fields include:

- `timestamp`
- `cluster_id`, `warehouse_id`, `node_id`
- `query_id`
- `path`, `target`, `log_level`
- `message`, `fields`, `batch_number`

Filter by timestamp and node or query identifiers before matching on message text. `exitAt` values ending in `Z` are UTC; keep the predicate in UTC unless a conversion is explicitly required. The target warehouse can appear in `warehouse_id`, in `user_agent`, or only inside the message, and it is unrelated to the warehouse that serves the query reading these logs.

## `{schema}.profile_history`

Useful fields include:

- `timestamp`
- `query_id`
- `profiles`, usually a VARIANT array
- `statistics_desc`, which maps statistic names to positions in each profile's statistics array

Never hard-code statistic array indices. Resolve the name you want through `statistics_desc` from the same record, because indices vary by version.

**`statistics_desc` can be NULL, and then there is no operator attribution to be had.** In one memory-panic investigation the failing query had `has_profile = NULL`, exactly one `profile_history` row written at the instant of death, `statistics_desc = NULL`, and a `profiles` value that was not an operator-statistics array at all but a per-node metrics blob (`{node_id: [{name: "opendal_operation_bytes_sum", value: ...}]}`). That blob cross-checked cleanly against `bytes_from_remote_disk`, so it is useful for IO volume — and useless for naming the operator that held the memory. When you land in this state, say that operator-level attribution is unavailable rather than guessing from the last log line.

Profiles can be sampled while a query runs. If the process exits abruptly, the newest record may not be final, and the presence of some operator metrics does not prove every operator reached its next sampling or final-flush point. A single record is a snapshot, not a time series: it cannot show growth, and it cannot show which operator grew. Interpret absent, zero, and partial statistics against the code that records them.

## Table and Output Pitfalls

- The default database may not contain logs. Always qualify `{schema}.<table>`.
- Discover table names instead of guessing them: `system_history` existed in one environment and not the one that motivated these notes.
- Large VARIANT, SQL text, and settings columns can overwhelm or truncate tool output. Aggregate first, select substrings such as `substring(message, 1, 500)`, and only widen once the shape is known.
- Bound large history scans with both the date partition and precise timestamp limits.
