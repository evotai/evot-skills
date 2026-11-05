# Modeling guide

## Start from the bad outcome

Build a property-directed model, not a line-by-line translation of the whole subsystem. Work backward from the agreed user-visible safety goal: what bad outcome is forbidden, which action could first cause it, what information or checks that action relies on, and which concurrent actions could invalidate them? Trace those dependencies against the bound source, retain the state and transitions that affect them, and test the smallest relevant interleaving first.

For example, a published reference could point to a deleted object if GC decides from an old view that the object is unused while a writer later publishes it. Inspect the read, deletion and publication steps and any actual version/fence checks between them. Use a witness to check that the suspected schedule is reachable.

This selects an investigation focus, not permission to omit relevant actions, protections, in-flight operations or failure paths. Record abstractions in `scope` and why omitted details do not affect this property; if that cannot be justified, include them or report the gap. Extend the dependency review as needed; a pass or an unreachable witness does not establish general safety. Do not require an inductive invariant or a TLAPS proof just to search for reachable bugs.

## Map code to actions

- Make one action per externally observable step: each metadata read, object read, write or delete, CAS or transaction, cache fill or hit, and directory listing.
- Split a step wherever another actor can run in between: an `await`, an RPC, IO, or a lock release. Merge steps only where the code is really atomic, such as a single CAS or in-memory work under one lock.
- Model the checks the code performs, in the order it performs them. Do not add a check the code lacks, and do not drop one because it looks redundant.
- Keep distinct values distinct: wall clock vs logical timestamps vs object modification time; the view an actor captured vs current state; physical existence vs cached contents vs published references.
- Keep immutable object contents after deletion, so stale reads and cache hits can be modeled. Track existence with separate sets.
- Model failure outcomes in scope: partial writes, abort after a side effect, a retry using a stale or returned view, leftovers that later actors observe.
- For retries, model the bound and exactly what is reused and what is reread.
- Verify the data shape the code really produces (links, pointers, ordering keys) against code, and ideally a real artifact. Code that rewrites links can make an apparent counterexample impossible.
- Environment actors may be collapsed into one atomic action. List that abstraction in `scope`, because counterexamples that depend on it are not evidence.
- Map every action in `source_map` as `"ActionA,ActionB": "path::function"`.

## Bounds

- Small domains: 1-2 of each actor, 1-2 operations, at most 2 retries. Sample time with few values, but cover ties and ordering ambiguities such as equal timestamps and ID tie-breaks.
- Use `constants` plus `matrix` for variants; every default case runs exhaustively.
- Terminal states are allowed and deadlock checking is off. Do not claim liveness.

## Invariants

- Primary: user-visible safety over physical state. Examples: every object referenced by published state exists; committed data is never lost.
- Distinguish a bookkeeping violation from real dangling references or data loss.
- Secondary: `TypeOK`, and structural facts the code guarantees, once verified from code.
- Write intentionally false reachability probes as `NeverX == ~(...)`.

## Controls

- **Mutation**: a boolean constant that disables one real protection, with a case `"violation": "Invariant"`. If no counterexample appears, either the protection is redundant within the bounds or the model cannot reach the danger. Investigate before trusting the normal pass.
- **Witness**: a `NeverX` probe for an important interleaving, such as a cache hit after delete, a retry after conflict, or GC observing an intermediate state. A witness case keeps every default safety invariant.
- Keep the set small. Each control should support a claim in the report.

## Iterate with a question

Before an exploratory rerun, state briefly in the existing work notes or report: the unresolved hypothesis, what changed in the model/configuration or diagnostic method, and the new evidence expected. Use the resulting trace or witness outcome to choose the next step; no separate ledger or schema is needed.

- Resolve source/model mismatches before expanding the search. For induction failures, check reachability and missing structural facts before reporting a bug.
- For state explosion, review abstractions and state representation; justify any larger bounds or resource budget. Never remove relevant behavior merely to finish.
- If formal proof was explicitly requested, split a stalled obligation or revise its abstraction rather than repeatedly submitting it unchanged.
- Unchanged reruns are appropriate for required regressions, reproducibility, or a justified transient-failure retry. Otherwise, if no new evidence or concrete next experiment is available, stop and report the unresolved question; ask before work beyond the agreed scope or budget. Resource exhaustion is not a pass or evidence that the property is false.

After authorized model/configuration changes, still run all normal cases, mutations and witnesses. This exploratory loop does not alter saved models in replay mode.

## Interleaving audit checklist

- Is every read that crosses an await split from the decision that uses it?
- Can another actor run between list/select and use, or between check and act?
- Caches: can a stale hit return contents of a deleted or replaced object, including on another node?
- Listings: does the code read a directory listing or walk committed ancestry? Are uncommitted or orphaned objects visible to it?
- Configuration branches: every mode that picks a different root or boundary, such as retention by time vs by count, or zero retention.
- Metadata rewriting: pointers or links rewritten before commit.
- Retries: conflict refresh, rebuild, timestamp resampling, maximum attempts, and the view each retry uses.
- Failure paths: abort after partial staging; state left for later actors.
- Time: monotonic adjustment, precision truncation, and offsets between derived timestamps.

## model.json

```json
{
  "module": "Protocol",
  "constants": {"Writers": 1, "CheckFence": true},
  "invariants": ["TypeOK", "PublishedRefsExist"],
  "matrix": {"Writers": [1, 2]},
  "cases": {
    "no_fence": {"constants": {"CheckFence": false}, "violation": "PublishedRefsExist"},
    "witness_retry": {"witness": "NeverRetryCommit"}
  },
  "scope": ["Bounds and abstractions, one fact per entry."],
  "source_map": {"WriterRead,WriterCas": "src/txn.rs::commit"}
}
```

- Constant values are booleans, integers or simple strings. `matrix` keys must be declared constants with nonempty value lists.
- Case names match `[A-Za-z0-9_-]+`. `constants` and `invariants` override the defaults. `violation` expects that exact invariant failure. `witness` adds a probe on top of the default invariants.
- Other keys (`scope`, `source_map`, `audit`, `regressions`) are documentation. Use `audit` for short records of resolved model errors.
- The runner generates `CONSTANTS`, `INIT Init`, `NEXT Next`, `CHECK_DEADLOCK FALSE` and `INVARIANTS` per case.

## TLA+ style

- One record variable per actor keeps `UNCHANGED` lists short.
- Comment non-obvious facts with the function they come from.
- Keep the module focused on one protocol. Add a sibling directory for another.
