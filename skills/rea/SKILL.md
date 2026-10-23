---
name: rea
description: "Reverse engineer native, managed, Electron/JavaScript, packaged, firmware, and browser targets with REA CLI. Use shipped-artifact or requested runtime evidence to explain features, compare versions, decompile code, or guide a reconstruction. Skip REA for ordinary source-repository analysis. Also 逆向、反编译、还原源码."
license: MIT
compatibility: Requires a working REA CLI and compatible Node.js; operations need their supported local engines. CLI-only, no MCP.
metadata:
  evot:
    requires:
      bins: [node]
---

# REA

Concise CLI-only adaptation of the official REA skill; see [upstream and changes](UPSTREAM.md).

Use REA for claims about shipped artifacts or requested runtime behavior. For a complete source repository, use normal repository tools instead.

## Boundary

- Analyze through **REA CLI and supported backends**. No MCP registration, server or bridge-dependent provider. No direct alternative analysis tools or substitute binary parsers, even wrapped in `capture-process`.
- Shell/file tools may stage inputs, hash artifacts, read saved Evidence, configure approved dependencies, write oracles and compile/test recovered code. They must not replace REA analysis.
- **Automatically diagnose and configure existing installations** when a capability is missing. Ask once before downloads, builds, installations or persistent configuration changes; after approval, perform the scoped setup and verify it rather than just handing over commands. Follow [connection and recovery](references/connection-and-recovery.md). A working CLI alone does not imply backend readiness.

## Investigate

1. Resolve target identity and questions; reuse matching saved Evidence. Do not repeat readiness checks without a failure or environment change. Follow the selected interface's actual help/tool schemas, not an assumed upstream catalog.
2. Route the target and read **only the relevant guide**:

   | Target | Guide |
   | --- | --- |
   | Native, managed, metadata, packages, containers | [Native and artifacts](references/native-and-artifacts.md) |
   | ASAR, JavaScript, feature tracing, versions | [JavaScript applications](references/javascript-applications.md) |
   | APK and Android code | [Android applications](references/android-applications.md) |
   | Process, browser/Electron observation | [Runtime observation](references/runtime-observation.md) |

3. Start with the smallest useful overview. Follow entry points, relevant state changes and results. Batch related operations around a hypothesis; expand only for a concrete gap. Preserve failures and report unsupported parts—do not bypass REA.
4. Work summary-first: save complete Evidence, then select bounded views/functions/pages. Each CLI call is a separate process; use portable records or explicit bundles rather than another call's in-memory ID. See [Evidence workflows](references/evidence-workflows.md).
5. Corroborate claims with the required evidence; runtime stays within the requested scope. For selection logic, test boundaries/overrides and assert the actual operator/backend as well as independent result correctness.

## Finish

Keep a concise ledger linking conclusions to Evidence IDs/locations, evidence type, search boundary and unknowns. Distinguish **observations, inferences and unknowns**; static analysis is not observed execution, and incomplete coverage is not absence.

Mark questions answered, partial or unresolved. Explain findings with supporting Evidence, actual runner/provider, setup changes, limitations and reproduction paths. If source is requested, deliver reconstructed files and tests labeled **not original vendor source**; separate recovered behavior from design choices. See [reconstruction](references/evidence-workflows.md#reconstruction).
