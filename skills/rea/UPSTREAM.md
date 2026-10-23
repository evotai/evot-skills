# Upstream

This unit adapts [morluto/rea's official skill](https://github.com/morluto/rea/blob/60accad2de8f2862fe91901502fe26cc5390fb36/.agents/skills/reverse-engineer-anything/SKILL.md), commit `60accad2de8f2862fe91901502fe26cc5390fb36` (reviewed 2026-10-23). Copyright (c) 2026 morluto; [MIT license](LICENSE). Source paths and SHA-256 values are recorded in [upstream.json](upstream.json).

## Local changes

- Keep the install name `rea`; condense the official entry and read only relevant guides.
- Adapt the official six playbooks to CLI commands and portable Evidence, not persistent server sessions. Retain target routing, summary-first work, provenance, coverage and observation/inference/unknown distinctions.
- Remove registration/connection repair, client configuration and bridge-dependent workflows. No MCP, direct alternative analysis tools or custom parser fallback.
- Automatically diagnose missing capabilities and repair unambiguous existing installations in the task environment. Downloads, builds, installations and persistent edits need one scoped approval, followed by execution, backend verification and resumption; never register MCP.
- Add container staging boundaries, expected backend assertions and reconstructed-source delivery/tests.

These are **adapted selections**, not an unchanged upstream distribution. The source commit pins these instructions, not the installed REA executable. An update must review CLI schemas, transport-specific behavior and license/provenance again; do not overwrite this profile by running setup.
