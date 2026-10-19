# Memory panics, OOMs, and node co-location

Load for memory incidents after the [incident workflow](index.md). Confirm the live [log schema](log-schema.md), serving org/API origin, subject tenant, and UTC time. This is read-only forensics, not permission to raise limits or resize compute.

A panic such as `memory usage 192.0 GiB(...) exceeds limit 192.0 GiB(...)` can describe the **process** tracker rather than a per-query ceiling. The query named in the alert can be the task that observed the panic, not the allocation that exhausted the node. Do not stop at that query.

## Work the protection ladder

1. Read `max_memory_usage` (node limit) and `max_query_memory_usage` (per-query limit) from that execution's `session_settings`. This field is a comma-separated `key=value` string, not JSON. Compare the recorded settings to the panic's number.
2. Read `peek_memory_usage` as a `{node_id: bytes}` map. Preserve the whole map or select specific keys. It represents the query's recorded footprint per node in the observed deployment, not a scalar or a verified node-wide total.
3. If that query is below its own ceiling, investigate shared-node workload using [co-location recipes](query-recipes.md). Another query below its own limit can still contribute to a process limit.
4. Check `query_out_of_memory_behavior`, `allow_query_exceeded_limit`, spilling ratios, `max_hash_join_spill_level`, `max_aggregate_spill_level`, and spill counters. Determine from the version's code whether the protection path should have engaged.
5. Cross-check query profiles, node/container exit evidence, and logs. State missing observations; do not invent unavailable operator attribution.

Zero recorded spill next to a panic supports a finding about absent recorded spilling; it does not prove why the protection path failed. Profile counters can be sampled, delayed, or absent at abrupt exit. A per-node metrics blob with NULL `statistics_desc` cannot name the memory-holding operator.

## Reconstruct shared-node overlap

Use the failing query's cluster ID and a narrow window. Include terminal rows **after** the incident because surviving neighbors can finish later. A previous investigation found a relevant neighbor's terminal row 2m47s after the victim died; ending the scan at the panic would have hidden it.

Resolve the same node in every memory map. Query lifetime overlap and recorded per-query peaks provide evidence of possible aggregate pressure. **Do not present the sum of independent peaks as measured simultaneous node usage** unless time-aligned samples prove it. Peaks can occur at different instants. Separate this upper-bound estimate from directly observed process/container memory.

Neighbors that never terminate in the justified observation horizon remain unquantified, not absent. If Start coverage is sparse, report that active-overlap reconstruction is incomplete.

## Conclusion requirements

Distinguish node pressure, a per-query limit, a container/kernel OOM, and a version-specific protection-path regression. They are not interchangeable. A last watchdog sample is not an allocation stack trace. Report which hypothesis is supported, the timing and resource evidence, competing explanations, and the next read-only check needed before calling it the root cause.
