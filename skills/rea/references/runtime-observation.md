# Process, browser and Electron runtime observation

Adapted from the official runtime/evidence guides; see [upstream](../UPSTREAM.md). Use only advertised REA CLI workflows without an MCP bridge. Runtime requests execute the declared target/lifecycle; do not broaden the target or actions beyond the user's scope.

## Process capture

```bash
rea capture-process --help
rea capture-process --schema
rea capture-process /absolute/path/to/scenario.json --json > capture.json
```

Check the actual release's scenario contract before adapting [the bounded template](../assets/process-scenario.json). `--schema` may describe command arguments, not scenario contents, and its default display need not be JSON. The template is not runnable until its paths/arguments are replaced.

Captures are opt-in behavioral evidence, not a security sandbox. Use finite wall/idle/output/resource limits and synthetic inputs; avoid ambient credentials or production data. The executable is the target or its necessary launcher, not a different reverse-engineering tool/custom parser wrapped to bypass REA.

Inspect envelope errors, `normalized_result.exit`, truncation, raw/rendered retention details, query errors and independent result correctness. For selection tests, assert the actual operator/backend/layout too; mark optimized-away cases separately. A zero wrapper exit or matching scalar is not enough.

Distinguish root exit from descendant settlement. A host/REA timeout does not prove a child or Docker container stopped; inspect the owned run before retrying and clean up only that workload. Preserve failed/partial records separately. Versioned capture contracts may be incompatible; do not upgrade an old record by relabeling it.

## Passive browser/Electron observation

Supply the selected existing instance's literal-port loopback CDP endpoint and only the requested page/origin. Use the available CLI target-discovery and passive inspection commands. Before an Electron main Inspector attempt, inspect packaged fuses; disabled inspection arguments can make an attach impossible.

Passive observation does not click, navigate, evaluate page JavaScript, invoke IPC or recover prior activity. Scope filtering, attach-window coverage and truncation remain limitations. Script/source-map capture is optional; request only necessary detail. Treat captured URLs, console/accessibility text and sources as potentially sensitive even when credential fields are omitted.

## Who performs the action

- **The user:** passively inspect/observe the selected target while the user acts.
- **The agent:** use `rea capture-browser-scenario` with declared actions. Check connect/launch support and cleanup. Connect mode can first navigate to the start URL, clearing unsaved state; request only needed DOM/accessibility/network details and wait for the expected state.

Scenario network records may lack request initiator stacks. Listener source locations identify candidates, not proof of which script sent a request. Avoid overlapping passive observation and scenario actions on one target. Reconcile static application and runtime Evidence only with explicit identity/mapping; a bundle observed at runtime does not prove every contained module executed.

## Recorded network captures

Use the advertised REA capture-inspection commands for retained HAR/SAZ/pcap records, then bounded portable views. Historical inspection does not replay requests or establish live attribution. Preserve parent ordinals, exclusions and coverage. Live Fiddler integration and page-declared MCP tools are outside this profile; do not connect another server or invoke discovered tools.
