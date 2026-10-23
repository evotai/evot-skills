# Native, managed, and packaged artifacts

Selected official playbook sections, adapted to CLI inputs and portable Evidence; see [upstream](../UPSTREAM.md). Check command availability and input schemas in the installed release. Engines are invoked through REA, not directly.

## Native targets

Start with `rea analyze`, focused `rea search`, `rea function`, `rea decompile` or `rea xrefs` according to the question and advertised provider. Prefer literal search, names, decompilation, callers, callees, and cross-references. Addresses and recovered pseudocode are analysis observations, not original source. Provider unavailability and unsupported metadata remain unknown rather than false.

For a completed function dossier, use `rea inspect-analysis-view` with a portable source and `view: {kind: "native", facet: "value_flow_operations", offset: 0, limit: 32}` when supported. Native facets include procedure, pseudocode, assembly, basic blocks, comments, callers/callees, references, unresolved calls, referenced strings/names, the native API record and value-flow summaries. Pseudocode offsets count UTF-16 code units. Preserve limitations; see [Evidence workflows](evidence-workflows.md).

`rea inspect-macho` on a large framework can return megabytes. Request a supported summary, then page exact slices/collections rather than repeating analysis. `source_exhaustive: false` means unreturned symbols may exist. For a declared runtime question, `rea observe-native-calls` launches a new process under LLDB through REA; the target can change files/network and hardened targets need the required entitlement. This is execution, not static inspection.

## Static memory and original file bytes

For Ghidra, `rea read-bytes` reads initialized analysis memory, including loader fixups; it does not read a running process. Check `returned_bytes` and `complete` before decoding a table. An incomplete read is missing coverage, not a zero-filled tail.

Use `rea address-to-file-offset` to anchor one observed address to original file bytes. A mapping for the first address does not establish a contiguous mapping for an entire table, and loader fixups can make analysis bytes differ from source bytes. Keep source ranges and analysis-memory observations separate.

A pointer table can refer to writable slots populated by a constructor rather than directly to immutable resources. An uninitialized block or an observed zero does not establish the slot's later runtime value. Follow REA xrefs and the relevant writer's assembly/pseudocode; distinguish assignments from inferred execution order. Do not replace unreadable bytes with zeros or conclude absence without initialization evidence.

## Apple resources and installation directories

The matching REA CLI plist, Interface Builder, asset catalog and keyed-archive commands accept an app path. Check the selected release's admission rules: resource-only support and executable requirements differ across versions. Preserve per-resource hashes and resource-root provenance; an app directory is not an executable digest or proof of provider readiness.

When an installation directory is supplied and its runtime is unknown, use `rea inspect-desktop-application` if advertised. Page `files`, `omissions`, `candidates`, `components` or `next_probes` through saved Evidence. Directory snapshot identity is not a digest of every file's contents. Component path markers do not establish runtime presence.

## Go build metadata

Use `rea inspect-go-binary` for an explicit ELF, PE or Mach-O when the question concerns compiler/module/dependency versions, local replacements or build settings. No native session, Go installation or target execution is required. Preserve artifact SHA-256, original file ranges, framed module bytes and every unparsed module-text line. A missing record is an unknown, not proof of a non-Go binary; observed metadata does not authenticate its claims. Function, source and type recovery remain a separate native-analysis question.

## Rust dependency metadata

Use `rea inspect-rust-binary` for the cargo-auditable crate list in `.dep-v0` (Mach-O: `__DATA,.dep-v0`). No Rust installation or target execution is required. Preserve artifact SHA-256, package order, dependency indices and section range. A missing section is null metadata, not proof the binary has no dependencies. An inferred rustc path does not by itself identify the compiler.

## Managed PE/CLI

Start with `rea inspect-managed-artifact`. REA's canonical managed inspection is execution-free: do not claim it loaded, reflected, executed, or resolved the assembly. Keep managed/native boundaries and unavailable reconstruction facts explicit. A bring-your-own reconstruction oracle is separate from the canonical parser and must not become an implicit setup dependency.

Use supported summary/member selection and portable `managed` / `managed-members` views for relevant references, attributes, resources, methods and call edges. Preserve build-local tokens and artifact/MVID scope; returned-row exhaustion is not complete metadata under partial coverage. NativeAOT is a native-analysis question, not managed IL decompilation.

## Other metadata routes

Use only advertised commands appropriate to the format:

| Input | REA CLI | Preserve / do not overclaim |
| --- | --- | --- |
| ELF | `inspect-binary-layout`, `inspect-elf-notes` | Analysis/file addresses, build-id ranges, coverage; layout is not runtime behavior. |
| PE | `inspect-pe-certificates`, `inspect-pe-resources` | Table/payload ranges and identities; a certificate table does not prove signature/chain validity. |
| WASM | `inspect-wasm-artifact` | Original module digest, imports/exports and declared limits; WAT is not original source. |
| SQLite snapshot | `inspect-sqlite-database` | Snapshot and sibling WAL identities, exact table/columns, finite samples and actual Node API support. |
| Model | `inspect-model-artifact` | Header-only metadata is not full weight identity; full hashing reads all bytes. |
| Unity metadata | `inspect-il2cpp-metadata` | Supported version/layout, artifact digest and scoped indices; code-address linking needs separate evidence. |
| Python / Erlang | `inspect-python-pyc`, `inspect-erlang-beam` | Bytecode/header provenance; inspection is not source decompilation. |

See the [pinned official native guide](https://github.com/morluto/rea/blob/60accad2de8f2862fe91901502fe26cc5390fb36/.agents/skills/reverse-engineer-anything/references/native-and-artifacts.md) for format/version boundaries. A command documented upstream is not necessarily installed locally.

## Packages and extraction

Use `rea inspect-artifact` for bundles, ZIP/APK/IPA/MSIX/AppX, ASAR, DMG or a supported embedded archive when inventory/graph findings answer the question. Cite graph manifest IDs. Application roles inferred from paths are not parsed configuration or proof of runtime presence.

Use `rea extract-artifact` when materialized files are needed. Read its reported destination/provenance and integrity policy; do not assume extraction accepts a caller-selected output path. Symlinks/encrypted entries may be inventory facts rather than extractable files. Native DMG mounts are host-specific and temporary; if REA cannot export the needed files, report that limitation rather than using an alternative analysis workflow.

For headerless inputs, use only REA's advertised format/architecture/entry-point options and verify the loaded image before trusting decompilation. Preserve the original and any derived artifact identities; an unpacking stub is not the unpacked program. Never interpret file offsets as virtual addresses without a validated mapping.

## Container input staging (evot adaptation)

Pin the selected platform manifest digest and extracted executable SHA-256. Docker metadata/copy operations may stage approved inputs without running the image's entrypoint; analyze the resulting file through REA. Use only an owned stopped container, copy necessary files, and remove that container. No home/Docker-socket/production-volume mounts or broad prune operations. A tag/index digest is not its selected platform manifest.

For target execution, use the approved Docker client as the REA capture launcher, with explicit image/entrypoint, synthetic inputs and resource/isolation limits. Follow [runtime observation](runtime-observation.md); capture is not a sandbox and its deadline may not stop the container.
