# Evidence, comparison, and verification workflows

Adapted from the official Evidence playbook and CLI contract; see [upstream](../UPSTREAM.md).

Evidence-producing CLI commands return complete JSON. Read `normalized_result` for operation data and cite `evidence_id` for identity. Preserve authority, limitations, coverage and residual unknowns. If a result is paginated, continue only when the remaining data matters; do not fetch a bundle just to reread returned facts.

## Portable CLI views

Each CLI invocation is a separate process. Another call cannot assume an in-memory retained Evidence ID still exists. Save complete records to task-local files before requesting views. The installed CLI may accept portable inline Evidence, an evidence-file source or retained IDs resolved from an explicit bundle; inspect its actual help/schema before choosing one.

A compatible inline request has this shape, where `COMPLETE_EVIDENCE_OBJECT` is a JSON object from the saved producer, not a string or ID:

```text
{"source":{"kind":"inline","evidence":COMPLETE_EVIDENCE_OBJECT},"view":{"kind":"summary"}}
```

Write the real request JSON using an existing JSON processor, then:

```bash
rea inspect-analysis-view /absolute/path/to/view-request.json --json > view-evidence.json
```

For large records, prefer supported file/bundle-backed input and bounded views rather than duplicating a huge record in model context. A retained ID is usable only with the authenticated bundle that contains it, supplied via the release's advertised argument. Do not invent an ID or assume a successful previous process exported a bundle.

Select module/function identities and exact rows before full items. Keep source completeness separate from page exhaustion. For example, native string/value inventory exhaustion does not establish complete program discovery. Do not repeat a successful producer merely to obtain a smaller display; reuse its saved Evidence.

## Evidence and comparisons

Every conclusion must distinguish observations, inferences and unknowns. Static differences are candidates, not causal proof. Absence requires compatible, complete coverage; unpaired observations need not mean additions/removals.

Use the installed REA comparison workflows with complete portable inputs: artifact/function or bundle comparison where available, `compare-application-versions`, `compare-process-captures`, and explicit static/runtime reconciliation. Names, module ordinals and matching patterns alone do not prove identity or causality. Preserve both artifact digests and input/scenario differences. Finite verification covers only declared comparable claims, not global equivalence.

Save raw records unchanged; index conclusions by Evidence ID, location, evidence type, search scope and unknowns. A truncated host preview is not canonical JSON. Narrow the view rather than parsing partial text, and inspect any recorded coverage/truncation before making a negative claim.

## Reconstruction

When the user asks for source, first check for matching published/original source. Otherwise deliver actual reconstructed files plus the important code inline, labeled **reconstructed, not original vendor source**. Keep observed behavior separate from implementation choices. Preserve artifact version/SHA-256, supporting REA Evidence/addresses, inferred names/types and omitted paths in a short provenance header.

Recover only the validated part: a pure selector is more honest than invented full hash tables. With an existing compiler, compile and run focused tests for branches, boundaries, state flags and overrides; do not install a toolchain silently. Compare against captured target behavior and assert the expected backend/layout as well as output. Report uncompiled/untested code honestly. Normal file editing and compilation are supporting work, not permission to replace REA with another reverse-engineering tool.
