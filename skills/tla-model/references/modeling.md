# Modeling guide

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
