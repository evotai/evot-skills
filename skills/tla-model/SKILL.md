---
name: tla-model
description: "Model concurrent, transactional, GC, cache, retry, replication or distributed logic in TLA+ from existing code or a design; check it exhaustively with TLC; map every action and counterexample step back to source. Use to hunt races and data-loss bugs, validate a fix or design, audit a model for missed interleavings, or explain a counterexample. Also 形式化验证、TLA+ 建模、TLC 模型检查、找并发 bug、反例对应代码."
license: Apache-2.0
compatibility: Requires Python 3.10+ and Java 11+. The pinned TLC jar (tla2tools 1.8.0) is downloaded once on request and verified by SHA-256.
metadata:
  evot:
    requires:
      bins: [python3]
---

# TLA+ model checking

Find implementation or design bugs, not a green TLC run. A bounded pass is not a proof, and TLC does not check correspondence with source code.

## Scope

Agree on the protocol, source commit/working tree or design revision, safety property, and file location. Default: no commits, CI integration or production-code changes. Keep one model per protocol; do not expand other models unasked.

## Workflow

1. **Check source consistency before running an existing model.** Follow [source consistency](references/source-consistency.md): compare the recorded baseline with the target revision and working-tree changes, including staged, unstaged and relevant untracked files. Review affected callers/helpers, not just mapped filenames. Unchanged semantics permits reuse; semantic changes require updating the model, mapping and controls. Regenerate only if the structure no longer fits. Unknown correspondence means unverified, not a current-code PASS. This is an agent review gate, not enforced by the runner.
2. **Read and model the actual protocol.** Follow [modeling](references/modeling.md). Trace reads, writes, CAS, caches, listings, retries, clocks and failures end to end. Split actions where another actor can interleave; model only checks the code actually performs. Record each action as `file::function` in `source_map`, bounds/abstractions in `scope`, and resolved model errors in `audit`.
3. **Add controls.** Keep user-visible safety properties distinct from type/structural facts. Use a mutation disabling one actual protection and expecting one exact violation; use witnesses for important interleavings. Never weaken safety, invent guards, or prune bad states to obtain a pass.
4. **Run small, then complete.** Use the commands below. After model/configuration changes, run all normal cases, mutations and witnesses. Timeouts, OOMs, parse errors and incomplete normal searches are not passes. Sampling is not exhaustive checking.
5. **Triage failures against code.** Follow [counterexample triage](references/counterexample-triage.md). Map the trace to implementation steps; classify model error, abstraction outside scope, or candidate bug. Correct model errors without weakening invariants, then rerun everything. If diagnosing a candidate *inductive* invariant, read [induction diagnostics](references/induction.md); a non-inductive candidate is not itself an implementation bug.
6. **Audit even after a pass.** Recheck the interleaving checklist against current code. Confirm candidate bugs with same-version native tests where feasible, using isolated resources. Ask before using shared machines/services, licenses or credentials.
7. **Record evidence.** Follow [repository and report conventions](references/repository-and-report.md): models-root `AGENTS.md`, per-model README, source review separate from TLC results, verdict first in the user's language. Recheck source/model changes during the run; never attribute old results to a newer snapshot.

## Run

Resolve script paths against this skill directory, not the project. Use external artifact directories; never commit generated configs, jars, logs or traces.

```bash
python3 scripts/tlc_run.py <model-dir> --list
python3 scripts/tlc_run.py <model-dir> [--case NAME ...] [--output NEW_DIR]
python3 scripts/tlc_trace.py <artifacts>/<case>/tlc.log [--vars a,b] [--final]
```

If the pinned jar is missing, ask once before `--download`. Java comes from `--java`, `JAVA_HOME`, or `PATH`. A mutation/witness `PASS` means its expected counterexample was found, not that the mutated implementation is safe. Default runs check safety, not liveness.

## References — load when needed

| Task | Read |
|---|---|
| Reuse a model against current code | [Source consistency](references/source-consistency.md) |
| Create/change a model or audit interleavings | [Modeling and manifest](references/modeling.md) |
| Explain a normal-case failure | [Counterexample triage](references/counterexample-triage.md) |
| Diagnose induction or prepare a proof | [Induction diagnostics and upstream sources](references/induction.md) |
| Create repository files or deliver results | [Repository and report conventions](references/repository-and-report.md) |
