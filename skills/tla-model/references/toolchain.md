# Pinned TLC artifact

## Identity and archive

The skill ships the **unmodified binary**, not a recipe to download whatever a release tag currently serves. The original pin is retained.

| Field | Value |
|---|---|
| SHA-256 | `e20447644bfabd29d6bd0fc2c0eb1473fb301c1a0e4dfe1961938ce5a191edbf` |
| Source repository | <https://github.com/tlaplus/tlaplus> |
| Source commit (jar manifest) | `309e489a512e8017f1cdc8388fa6a5e8a01cf597` |
| Build ID (`X-Git-BuildNumber`) | `master__309e489` |
| Build timestamp (`Build-TimeStamp`) | `2026-11-03T18:09:53.565Z` |
| Implementation version | `2.0 2026-11-03` |
| Archive within the skill | `assets/sha256/e20447644bfabd29d6bd0fc2c0eb1473fb301c1a0e4dfe1961938ce5a191edbf/tla2tools.jar` |
| Runtime cache | `~/.cache/evot-tlc/sha256/<full-sha256>/tla2tools.jar` |

The archive was recovered from an existing local cache and verified against the runner's original full SHA-256. The commit, build ID and timestamp above were read from that binary's `META-INF/MANIFEST.MF`; they are build provenance, not a claim of an independently reproduced build. `tlc_run_test.py` checks these fields against the archived jar. Each run writes the same identity to `toolchain.json` in its external artifact directory.

The historical download URL was `https://github.com/tlaplus/tlaplus/releases/download/v1.8.0/tla2tools.jar`. **It is mutable and is not an acquisition source.** The old filename `tla2tools-1.8.0.jar` did not identify the actual source commit or implementation version. The runner never contacts that URL, looks up the latest GitHub digest, or accepts a different hash. A mismatch means only that the bytes are not this pinned artifact; it is not, by itself, evidence of tampering.

The binary is stored as a regular Git blob (not Git LFS or an expiring CI artifact), travels with the installed skill, and remains available in the skill revision's Git history. Preserve this directory when packaging/installing the skill. This deliberately vendored dependency is distinct from generated jars/logs/traces, which still must not be committed to model repositories.

## Installation and recovery

- An existing cache or explicit `--jar PATH` is checked on every run. `--jar` does not override the expected digest.
- For an empty cache, ask once before `--install`. It copies from the bundled archive **offline**; `--download` remains an alias for existing callers and performs no network request.
- A verified legacy `~/.cache/evot-tlc/tla2tools-1.8.0.jar` can be copied into the content-addressed cache without installation consent; the old file is retained. A mismatched legacy cache is rejected, never relabelled or silently replaced. Move it aside explicitly before installing the archived artifact.
- Installation verifies the source, copies to a same-directory temporary file, flushes/syncs, verifies the staged bytes, and atomically renames. Failed copies/checks do not publish a partial jar. Existing mismatched destination files are not automatically replaced, even with `--install`.
- Deleting the runtime cache does not lose the pinned bytes: install again from the bundled archive. If the archive is missing, reinstall the **same skill revision including its assets**, or supply the exact verified artifact with `--jar`. There is no floating-URL fallback.

A dependency upgrade is a deliberate new toolchain revision: retain the old archive for replay, archive the new bytes under their complete digest, record their full source commit and build identifiers, update the runner identity, and review/run its tests. Do not repair acquisition failures by changing the expected hash, auto-trusting upstream replacements, or disabling verification.

## Licenses and source

The jar is redistributed without modification. The TLA+ Tools MIT license is retained inside `License.txt` and copied to `assets/LICENSE-tla2tools.txt`. Embedded third-party licenses/notices (including `META-INF/LICENSE.md`, `CommonsMath-LICENSE.txt`, `CommonsMath-NOTICE.txt`, and `jline-LICENSE.txt`) are preserved in the jar. Corresponding upstream source for this build is available at <https://github.com/tlaplus/tlaplus/tree/309e489a512e8017f1cdc8388fa6a5e8a01cf597>.
