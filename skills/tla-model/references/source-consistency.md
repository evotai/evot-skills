# Source versions: replay by default, synchronize explicitly

Every code model directory must record its source repository and full commit in README. A branch name or PR number alone is not a stable binding. Design-only models record a versioned document instead. Keep this binding separate from the model's own revision/hashes and from the latest TLC result.

## Default: replay the bound model

Requests such as “run TLA”, “rerun this model” or “run smoke” execute the saved model/configuration for its recorded baseline. Do not scan the current branch or working-tree diff, automatically repair the model, update the binding to HEAD, check out another revision, or add tests. Differences from current code are reference information, not permission to synchronize. If the binding is missing or ambiguous, ask instead of inventing one from HEAD.

Report the bound source commit, actual model/configuration hashes, checks and artifact path. Leave repository files unchanged. A failed replay remains a failure; diagnose against the bound source version and ask before fixing the model. Source can be read at that revision without switching the user's working tree. If unavailable, report that trace-to-code correspondence cannot be confirmed; TLC may still replay the saved model.

## Explicit sync: validate a requested source target

Only requests such as “validate the current branch/PR/latest code” or “check consistency with current code” authorize synchronization to that target. A generic model-edit request stays on the existing bound commit unless the user also requests a new source target; new models bind to the agreed source revision. For a PR, establish whether the target is its head or merge result, then record the resolved full commit. For a dirty tree, record the base commit plus the reviewed patch identity. Never silently rewrite the baseline or transfer old results to the new target.

TLC checks the supplied model, not its correspondence with implementation. The following review applies to **sync mode only** and is not automatically enforced by the runner.

### Identify the target

Read the model README's source baseline, `model.json.source_map`, `scope`, and `audit`. Decide whether the target is a clean commit, a PR revision, or the working tree. Do not silently substitute HEAD for a dirty working tree.

From the source repository, with `BASE` set to the recorded full commit:

```bash
git rev-parse HEAD
git status --short --untracked-files=all
git cat-file -e "$BASE^{commit}"
git diff --name-status --find-renames "$BASE" HEAD
git diff --name-status HEAD
git diff --cached --name-status
git ls-files --others --exclude-standard
```

Review patches, not just filenames:

```bash
git diff --find-renames "$BASE" HEAD -- <affected-paths>
git diff HEAD -- <affected-paths>
git diff --cached -- <affected-paths>
```

The working-tree diff against HEAD includes the net staged and unstaged changes; inspect the index separately if that is the target. Read relevant untracked source files explicitly: git diff omits them. If the baseline is absent, history unavailable, or source mapping missing, re-establish correspondence from current code before claiming current-code coverage.

### Review semantics, not only mapped files

Start with the repository-wide changed-file list. Follow affected callers, helpers, metadata types, serializers, feature flags, defaults, dependency changes and tests into `source_map`. A diff outside the mapped filenames can still alter the protocol.

For affected actions, check ordering and atomicity, lock/await boundaries, CAS conditions, failure side effects, retries and retained state, timestamps and precision, cache visibility, object/history links, listings and retention selection. Revisit assumptions and the interleaving checklist in modeling.md. Matching commits or an empty diff is not evidence that the original model was correct.

| Finding | Required action |
|---|---|
| No relevant change, previously reviewed correspondence still valid | Reuse the model; record the reviewed target and why reuse is justified. |
| Comments, formatting or a behavior-preserving rename/refactor only | Verify behavior preservation; update source mapping if needed, without regenerating TLA unnecessarily. |
| Protocol semantics or observable interleavings changed | Update affected actions, state, bounds, mappings and controls. Regenerate the model only when its structure no longer fits. Preserve safety properties unless the user explicitly changes the specification. |
| Change depends on an omitted actor or behavior | Refine the same model within agreed scope, or report the gap; do not silently exclude the changed behavior. |
| Correspondence cannot be established | Mark it unverified. Historical-model runs may be diagnostic, but are not validation of current code. |

### Run and record

- After model/configuration changes, rerun all normal cases, mutation controls and witnesses. Never carry forward old PASS counts as new results.
- Keep source-review status separate from TLC status. Review can succeed while TLC fails; TLC can pass while source correspondence is unverified.
- Record the reviewed source snapshot in the README: full commit, clean/dirty status, review conclusion, and the last run's model/configuration identity. For a dirty target, save relevant patches/untracked file copies and SHA-256 hashes in the external artifact directory; a commit hash alone is insufficient. Do not include secrets.
- Check the target and model/configuration for changes again after the run. If they changed during execution, results belong only to the captured versions; review and rerun before attributing them to the newer state.
- Keep prior results attached to their original revisions. Do not merely replace the README's commit hash to make an old model appear current.
