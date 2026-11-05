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

The goal is to find real bugs in the implementation or design. A green TLC run is not the goal, and a bounded pass is not a proof.

## Agree on scope first

- The logic to model and its source of truth: code at a commit, a PR, or a design doc.
- The safety property in the user's terms, e.g. "a published table never references a deleted file".
- Where files live. Follow the repository's existing layout; otherwise propose `tests/tla/<model_name>/`. One directory per protocol, containing `<Module>.tla` and `model.json`. No generated `.cfg`, traces, jars or long READMEs in the repository.
- Default: no commits, no CI integration, no production-code changes unless asked.

## Workflow

1. **Read before modeling.** Follow the code path end to end: reads, writes, CAS/transactions, caches, listings, retries, timestamps, abort and failure paths, and existing regression tests. Note `file::function` for each step as you go.
2. **Write the model.** Follow [modeling](references/modeling.md): one action per externally observable step, split wherever another actor can interleave, only the checks the code really has, distinct clocks and views, and physical existence kept separate from cached contents and published references. Record bounds and abstractions in `model.json.scope` and every action in `source_map`.
3. **Add controls before trusting a pass.** For each key protection add one mutation case (a constant that disables exactly that code check, expecting one exact invariant violation) and witnesses for the important interleavings. A pass without controls tells you nothing.
4. **Run**, starting with the smallest configuration:

   ```bash
   python3 scripts/tlc_run.py <model-dir> --list
   python3 scripts/tlc_run.py <model-dir> [--case NAME ...] [--output NEW_DIR]
   ```

   If the jar is missing, ask once, then add `--download`. Java comes from `--java`, `JAVA_HOME`, or `PATH`. `PASS` on a mutation or witness means the expected counterexample was found. Timeouts, OOMs, parse errors and `states left on queue` in a normal case are failures, not passes.
5. **Triage every normal-case failure** with [counterexample triage](references/counterexample-triage.md):

   ```bash
   python3 scripts/tlc_trace.py <artifacts>/<case>/tlc.log [--vars a,b] [--final]
   ```

   Map each step to code and classify the failure as a model error, an abstraction outside scope, or a candidate bug. Never weaken an invariant, add a guard the code lacks, prune bad states, or relabel the failure as expected to make it pass.
6. **Audit after it passes.** Walk the interleaving checklist in [modeling](references/modeling.md) against the code. Missed interleavings are the most common reason a model passes while the code is wrong.
7. **Confirm candidates natively** when feasible: same-commit binary or tests, isolated storage, metadata and ports, replaying the trace order. Ask before using shared machines, services, licenses or credentials.

## Report

Use this template for every final report. Write it in the user's language, keep the section order, and omit any section that has no content. Put the verdict first. No preamble, no recap at the end.

````markdown
**Verdict:** <one sentence: confirmed bug | model error, fixed | not reproduced | passes within bounds>, <the key reason>.

## Scope
- Logic: <code at commit or design>, <main files::functions>
- Property: <safety property in user terms>
- Bounds: <actors, operations, retries, time samples>; abstractions: <the ones that matter>

## Results
| Check | Result | Distinct states |
|---|---|---|
| Normal configurations (N) | all exhaustive / K failed | <total> |
| Mutation controls (M) | each found its expected violation | |
| Witnesses (W) | all reachable | |

## Counterexample
<case name>: <invariant>, <classification>.

| Step | Action | Code | Effect |
|---|---|---|---|

- Protection lost at step <n>: <what was not recorded or checked>
- Final state: <what exists> vs <what is still referenced>
- Evidence: <code line, real artifact, or native run result and which check fired>

## Not covered
- <behavior outside the bounds or model>

## Rerun
```bash
<command>
```
Artifacts: <path>
````

- The counterexample section is for normal-case failures, or a trace the user asked about. For a deliberate mutation, name the code line the mutation removes and say it is not a bug.
- List step rows for the relevant actions only. Merge consecutive steps that change nothing relevant into one row, e.g. "14-17".
- A bounded pass is never called a proof, and a model error is never reported as a bug.
