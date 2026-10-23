# evot-skills

Official skill catalog for [evot](https://github.com/evotai/evot).

## Usage

Official skills are installed and updated automatically. To manage them manually:

```text
/skill install                  # install all
/skill install databend-cloud   # install one
/skill update                   # update installed skills
```

Installed copies live in `~/.evotai/skills/`. Updates overwrite local edits.

## Catalog

| Unit | Purpose | Needs |
| --- | --- | --- |
| `databend-cloud` | Connect, query, manage authorized resources, and investigate Databend Cloud incidents | `python3`, private API key file or environment key; optional `jq` for readable log exports |
| `lark` | Work with Feishu messages, docs, and calendars | `lark-cli` |
| `opencli` | Browse, research, and automate the web | `opencli` |
| `rea` | Reverse engineer binaries, containers, and packaged applications through REA CLI with reproducible evidence and reconstructed source | Compatible Node.js and working REA CLI; task-specific REA backends, Docker for container tasks |

### REA in evot

[rea/SKILL.md](skills/rea/SKILL.md) is a concise **CLI-only adaptation of the official REA skill**, with its six playbooks loaded only as needed. [Upstream provenance](skills/rea/UPSTREAM.md) pins the source commit, records local changes and preserves the MIT license. This is an adapted selection, not an unchanged upstream distribution.

Use REA's installed CLI commands and supported backends; no MCP registration, bridge-dependent provider, direct alternative analysis tool or custom-parser fallback. [Connection and recovery](skills/rea/references/connection-and-recovery.md) automatically diagnoses runner/provider failures and configures unambiguous existing installations for the task. Downloads, builds, installations and persistent edits require scoped approval; after approval the agent completes setup, verifies the actual backend operation and resumes, without registering MCP. Compatible Node.js and a working REA CLI are required. Each invocation is independent: [Evidence workflows](skills/rea/references/evidence-workflows.md) use saved portable records or explicit bundles, not assumed cross-process session IDs.

No evot binary change is needed. Once published, install with `/skill install rea`; normal official-skill updates apply. Installing instructions does not install REA/engines or register MCP. Shell/file tools can stage approved inputs, process saved Evidence and compile/test reconstructed code. Source requests still require actual reconstructed files/tests, not claims of original vendor source.

### Databend Cloud in any agent

The Databend Cloud skill also works outside evot. Install the complete skill directory through your agent's skill mechanism, or read its `SKILL.md` and run the included Python scripts. No MCP server or third-party Python packages are required.

Start with [databend-cloud/SKILL.md](skills/databend-cloud/SKILL.md). The metadata records the skill version and last modification date; [CHANGELOG.md](skills/databend-cloud/CHANGELOG.md) records changes. Credentials live outside the repository in separate `~/.config/databend-cloud/credentials/<api-host>.json` files (or are privately injected with a bound API origin). Pass the real Organization ID as `--org` on every query, with the confirmed `--base-url`; warehouse defaults to `default`. There are no local org aliases or extra org-configuration commands. Both sites can coexist without replacing another site's key or switching global state. Re-running `set-key` updates only the same origin's key after valid input.

The skill includes authentication, organization selection, a personal-token API capability map, query lifecycle helpers, authorized warehouse management SQL, SQL documentation discovery, diagnostics, and error references. Incident workflows and exports live under `references/troubleshooting/` and load only when needed. One shared connection/query implementation serves every task; `jq` is optional for readable log exports, not ordinary queries or raw exports. Unrelated host connection settings are ignored.

## Contributing

Each directory under `skills/` is one install unit: a single skill or a group installed together.

```text
skills/
├── databend-cloud/
│   ├── .display.json
│   └── SKILL.md
└── lark/
    ├── .display.json
    ├── lark-im/SKILL.md
    └── lark-doc/SKILL.md
```

Follow the [Agent Skills specification](https://agentskills.io/specification). Each `SKILL.md` needs a unique `name` matching its directory and a `description` explaining when to use it. Groups cannot nest; file references must stay within the install unit.

### Test fixtures

Use only invented organization/account names, synthetic keys, and fictional IDs in tests and examples. Never copy production account identifiers, emails, hostnames, query IDs, or log records into fixtures. Offline tests must isolate credentials in temporary directories, avoid network access, and not read the developer's Cloud settings. Use reserved `.invalid` hosts for unrelated dummy endpoints; the official API hostnames may be used to test site selection without sending requests.

### Startup display

Add one `.display.json` at the unit root:

```json
{
  "schema_version": 1,
  "summary": "Work with Feishu messages, docs, and calendars",
  "example": "lark: What's new in my alerts group?"
}
```

Use single-line, printable ASCII text without surrounding whitespace: `summary` up to 60 characters; `example` up to 96, starting with `unit-name: `. These fields are for display only, not model instructions.

### Prerequisites

Declare dependencies in `SKILL.md` frontmatter:

```yaml
metadata:
  evot:
    requires:
      env: [SERVICE_API_KEY]
      bins: [python3]
```

Store secrets through the host's private secret settings or the skill's documented user-level credential mechanism, never in this repo. Do not require an environment variable when the skill also supports a credential file.

## Validation

```bash
python3 scripts/validate.py
python3 -m unittest discover -s tests -v
python3 scripts/run_tests.py
```

CI checks layout, frontmatter, display metadata, references, and file safety, then runs validator and skill tests.
