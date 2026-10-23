# CLI connection and recovery

Adapted from the official connection/recovery and native deadline guides; see [upstream](../UPSTREAM.md).

## Use an existing runner

Prefer an installed `rea`. If it works and its capabilities are known, proceed to the target; do not run diagnostics before every investigation. Check the environment only when needed:

```bash
command -v rea
command -v node
node --version
rea --version
rea --help
```

Use the public launcher at its known installation path when a child shell loses a prefix installation. A caller-selected built checkout can use `node /absolute/path/to/rea/scripts/rea.mjs`; check launcher prerequisites first. A source checkout alone is not a working installation. Avoid internal `dist/cli.js` entrypoints and global toolchain changes.

If acquisition is authorized, a reproducible package fallback is `npx --yes rea-agents@6.7.0`. Use `--offline` when the exact package is cached and network acquisition is not authorized; do not silently retry online. Verify the selected distribution's Node engines. The source commit used for these instructions is not the installed CLI version, and an older release may lack a documented capability. Do not switch to `latest` or acquire dependencies without approval.

## Automatic diagnosis and configuration

A working REA CLI does not imply an available native engine. On a missing capability or `provider_unavailable`, inspect REA's actual provider/capability diagnostics and the relevant command's help. Diagnose the failed lane once; do not repeatedly run the same failed search or check unrelated providers.

**Existing installations, no persistent changes:** automatically inspect known install locations or caller-supplied paths for the needed runner, compatible JDK and selected engine. On macOS, `/usr/libexec/java_home -V` can inventory installed JDKs; `/Applications`, known package-manager prefixes and the caller's selected extraction directory can locate an engine. Do not scan the whole home, dump the environment, run arbitrary discovered scripts or infer macOS incompatibility from missing software. Use REA diagnostics to validate host/architecture, engine and Java versions. An app path alone is not readiness.

When one compatible installation is unambiguous, set only the documented variables (such as `GHIDRA_INSTALL_DIR`, `JAVA_HOME` or PATH) for the current REA process/task, then retry the relevant check. Shell variables do not persist between tool calls: carry the validated environment explicitly or use a task-local runner. Do not edit shell profiles or global configuration as a temporary fix. Ask the user to choose when multiple incompatible/ambiguous installations exist.

**Acquisition or persistent changes:** present one scoped plan and ask for approval before downloads, builds, installations, license acceptance, elevated access or persistent configuration edits. Name the chosen engine/JDK, pinned versions, source, destinations, affected files and rollback. Prefer one suitable non-MCP backend, not every provider. Once approved, perform that setup within the approved scope rather than merely returning commands; ask again only if scope changes. Use official sources, verify available vendor checksums/signatures, back up affected configuration and preserve unrelated keys. Do not pipe remote scripts into a shell or silently accept commercial terms. Stop on failure and retain diagnostics.

**No MCP:** neither automatic repair nor installation approval authorizes registering/starting MCP or configuring a bridge-dependent provider. If a backend requires MCP, select an available non-MCP REA engine or report the blocker. Permission to configure software is not permission to execute the target or access production data.

## Verify and resume

Rerun the relevant REA provider/doctor check with the configured environment, then a bounded read-only REA operation on an approved artifact using the selected engine. Require both successful command status and an error-free result envelope; a green shell exit, `--help`, metadata-only inspection or JS capture does not prove native analysis works. Avoid masking a failed command with a later successful `printf` or pipeline. Save actual exit status, full JSON, stderr, engine/version/environment paths and any limitations; redact secrets.

Resume the interrupted analysis only after that check succeeds. Record what was changed, backup/rollback paths, and whether settings are task-local or persistent. If verification fails, do not call setup successful or repeat the unchanged call: report partial setup and the exact remaining blocker.

## Choose the remedy from the observed failure

| Failure | Action |
| --- | --- |
| Missing runner or incompatible Node | Discover existing compatible installations and repair the task environment; obtain approval before acquiring/building/upgrading. |
| Invalid arguments | Inspect that command's live help/schema; do not guess flags or mechanically translate upstream tool names. |
| Provider unavailable | Inspect `rea providers --json`, `rea capabilities --json` and the relevant diagnostics; configure a compatible existing engine, or complete an approved scoped installation. No MCP bridge. |
| Host call timed out without REA output | Do not assume the owned workload stopped or repeat the unchanged call. Check its state and saved outputs first. |
| REA returned `provider_timeout` | Adjust only the relevant documented budget when justified; narrower queries may still require cold import. |
| Unsupported operation | Preserve the error and partial Evidence, continue independent supported work, and report the missing capability. No direct-tool fallback. |

A provider failure affects that lane, not all REA operations. Static JavaScript and managed/Go metadata inspection do not universally need a native engine. Do not repair a PATH or engine problem by registering MCP.

## Deadlines

The host command deadline, REA/provider deadline and target/container lifetime are different. Extending one does not extend the others. For Ghidra startup, the official guide documents `REA_GHIDRA_STARTUP_TIMEOUT_MS`; set it in the environment of the next CLI invocation only when justified. Preserve host CPU/memory controls and original limitations. A larger budget is not a completion guarantee.

Check owned tasks/containers before retrying or cleaning up. Do not kill unrelated processes, duplicate state-changing captures or reuse a failed run's output files. Never spoof backend versions, invoke a different engine directly, or wrap it in REA capture to bypass a blocker.
