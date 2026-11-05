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

Agree on the protocol, safety property, and file location. Bind every code model to a full source commit in its README; bind design models to an explicit design revision. Default: no commits, CI integration or production-code changes. Keep one model per protocol; do not expand other models unasked.

**Default is replay, not synchronization.** “Run this model” means run its saved TLA/configuration against its recorded source baseline. Do not scan current code changes, edit the model, switch branches or relabel results as current-HEAD validation. Only an explicit request to validate the current branch, PR, latest code or source correspondence enters sync mode. See [source versions and modes](references/source-consistency.md).

## Workflow

1. **Select replay or explicit sync.** In replay mode, read the recorded source baseline and run the saved model without a source diff scan or automatic correction; ask if the binding is missing. In sync mode, follow [source consistency](references/source-consistency.md): compare baseline and requested target, review affected callers/helpers and dirty files, then update the model only for semantic changes. Change the binding only after review. The runner does not verify correspondence. For replay, skip modeling/controls changes and go directly to Run.
2. **Read and model the actual protocol.** Follow [modeling](references/modeling.md). Trace reads, writes, CAS, caches, listings, retries, clocks and failures end to end. Split actions where another actor can interleave; model only checks the code actually performs. Record each action as `file::function` in `source_map`, bounds/abstractions in `scope`, and resolved model errors in `audit`. When reusing a proof, [check its premises against the implementation](references/induction.md#reuse-a-proof-only-after-checking-its-premises); never assume the code satisfies them.
3. **Add controls.** Keep user-visible safety properties distinct from type/structural facts. Use a mutation disabling one actual protection and expecting one exact violation; use witnesses for important interleavings. Never weaken safety, invent guards, or prune bad states to obtain a pass.
4. **Run small, then complete.** Use the commands below. After model/configuration changes, run all normal cases, mutations and witnesses. Timeouts, OOMs, parse errors and incomplete normal searches are not passes. Sampling is not exhaustive checking.
5. **Triage against the bound source revision, not incidental HEAD.** Follow [counterexample triage](references/counterexample-triage.md). Classify model error, abstraction outside scope, or candidate bug. A replay request does not authorize model repair: report the mismatch and ask before changes. When repair is authorized, preserve invariants and rerun everything. For a candidate *inductive* invariant, read [induction diagnostics](references/induction.md); non-inductiveness alone is not an implementation bug.
6. **For modeling/audit requests, review even after a pass.** Check interleavings against the bound source (or explicitly requested sync target). Confirm candidate bugs with same-version native tests where feasible, using isolated resources. Ask before using shared machines/services, licenses or credentials.
7. **Record evidence.** Follow [repository and report conventions](references/repository-and-report.md), verdict first in the user's language. Replay leaves model files and binding unchanged; report its baseline, model hashes and external artifacts. For authorized modeling/sync, update README and check for source/model changes during the run. Never attribute old results to a newer snapshot.

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
| Choose replay vs explicit source synchronization | [Source versions and consistency](references/source-consistency.md) |
| Create/change a model or audit interleavings | [Modeling and manifest](references/modeling.md) |
| Explain a normal-case failure | [Counterexample triage](references/counterexample-triage.md) |
| Reuse a proof, diagnose induction or prepare a proof | [Proof premises and induction diagnostics](references/induction.md) |
| Create repository files or deliver results | [Repository and report conventions](references/repository-and-report.md) |
