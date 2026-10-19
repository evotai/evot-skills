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
