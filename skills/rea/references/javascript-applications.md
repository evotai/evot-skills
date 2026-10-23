# JavaScript and Electron application artifacts

Adapted from the official JavaScript playbook; see [upstream](../UPSTREAM.md). Use the installed command's CLI flags/schema. Each invocation is independent: save portable Evidence instead of assuming a retained server session.

## Analyze once, then select

Use `rea analyze-javascript-application` directly on the operator-supplied ASAR or extracted tree. No native engine is required for static JavaScript inspection. Save complete CLI JSON to the authorized workspace before reading a view:

```bash
rea analyze-javascript-application /absolute/path/to/app --json > app-evidence.json
```

When the release supports source selection, select exact inventoried paths and include needed manifests/source maps explicitly; dependencies are not implicitly analyzed. Omit selection for a complete application question. An empty selection is not an unfiltered request. Summary delivery reduces output, not necessarily analysis work.

For readable source recovery, use the advertised `recover-javascript-sources` workflow and only its supported inputs/provider/host. Preserve every input digest and byte-range provenance. Recovery is not execution; do not install a source-recovery engine automatically.

## Read a module without repeating analysis

Build an `inspect-analysis-view` request from the saved full Evidence as described in [Evidence workflows](evidence-workflows.md#portable-cli-views). First request a bounded module page:

```json
{"kind":"page","collection":"modules","offset":0,"limit":16}
```

Select the returned exact `node_id` and recorded role for an item:

```json
{"kind":"item","collection":"modules","selector":{"node_id":"REPLACE_WITH_RETURNED_NODE_ID"}}
```

These objects are **view fields**, not complete CLI requests. A path can represent asset, bundled and source module roles; use a path selector only when uniqueness is established. On ambiguity, select a returned node ID rather than guessing. Follow `coverage.next_offset` only as needed. Item facts do not include every child syntax observation or related edge; absence from an item is not absence from the application.

For canonical identities and source-range counts, use a supported `javascript` references projection with exact filters. Preserve row identity/support states. Counts describe retained observations, not runtime imports or execution. Page exhaustion covers matching retained rows, not necessarily the whole application.

## Trace only the remaining question

Use `rea trace-application-feature` with portable parent Evidence for one literal node ID, route, string, API, IPC channel, module or native export. Confirm its actual request-file syntax in help. Choose incoming/outgoing/both deliberately: containment traversal can reach unrelated sibling modules. Prefer an item/page if it already answers the question.

Include native Evidence only when its artifact digest matches exactly. BrowserWindow preferences, preload/contextBridge surfaces, IPC registrations and native binding requests are static syntax observations. Only a unique exact literal IPC channel match supports an inferred pairing. Dynamic or ambiguous channels remain unresolved. A requested `.node` member is not a verified native export. Never claim runtime reachability, registration, defaults, or policy enforcement from static analysis.

## Partial results and version comparison

Treat truncated display, incomplete source selection, analyzer limits and unknown graph relationships separately. Save partial Evidence returned by REA and inspect its covered facts; do not rerun a successful producer just to reproduce an oversized display. Missing preview fields are not proof of absence.

For version comparison, analyze each version once, then use `rea compare-application-versions` with both portable records. Accept only its digest, source-map, structural fingerprint or semantic matches. Module ordinals/minified names are not persistent identity. Claim added/removed only with complete opposite-side coverage; otherwise report unknown.

For an exact exported callable's returned shape, use `rea compare-javascript-export-shapes` if advertised. Preserve property inventories, pointer locations and presence/unknown states. Static shape inference is not runtime semantics; capture actual behavior through the supported browser, Electron or process workflows when required.
