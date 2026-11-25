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
| `agent-browser` | Navigate websites, fill forms, capture screenshots, and test web UIs in an isolated browser | Automatically installs the CLI via existing npm or Homebrew and downloads a missing browser on first use |
| `databend-cloud` | Connect, query, manage authorized resources, and investigate Databend Cloud incidents | `python3`, private API key file or environment key; optional `jq` for readable log exports |
| `harden` | Stress-test plans and module layouts; review git changes for merge readiness and required fixes | None |
| `lark` | Work with Feishu messages, docs, and calendars | `lark-cli` |
| `opencli` | Use structured site adapters and workflows needing existing Chrome login state | Automatically installs/updates the CLI via existing npm; browser-backed commands also need Chrome and the OpenCLI extension |
| `tla-model` | Model concurrent or distributed logic in TLA+, check it exhaustively with TLC, and map counterexamples back to code | `python3`, Java 11+; exact TLC jar archived with the skill and installed offline on request |

### Harden

`/harden` checks the latest concrete plan, strategy, or conclusion in the
conversation. If there is none, it checks local git changes instead; it asks
for a subject only when neither is available. `/harden changes` explicitly
selects git changes, and `/harden <target>` selects the named subject.

For git changes, the report starts with a verdict on the reviewed snapshot:
**mergeable**, **not mergeable**, or **merge readiness unverified**. It separates
blocking findings from optional follow-ups and ends with a checklist of only
what must be fixed or verified before merge. Missing evidence is not a confirmed
defect. Plan reviews instead say whether the approach can proceed and end with
a revised plan.

All forms are read-only by default. Only an explicit user request to implement
the findings authorizes edits. A merge verdict does not authorize merging.

### Browser tools

Use `agent-browser` for general website navigation, forms, screenshots, and web UI tests. Prefer dedicated service skills or OpenCLI site adapters when they already cover the operation; use OpenCLI's browser bridge when the task specifically needs your existing Chrome login or an in-progress tab. The tools do not share browser sessions or element references.

`agent-browser` automatically installs its missing CLI and downloads a missing browser when a task first needs them, then continues without a manual setup step. It prefers a user-local npm installation and reuses existing installations. OpenCLI checks for a newer stable CLI release once at the start of each task and automatically installs or updates into a user-local directory when needed. Both skills follow an observe–act–verify loop, consult live instructions, and resolve routine setup, login, and execution errors autonomously through to a verified result. Installing either skill itself does not trigger CLI or browser setup.

### Databend Cloud in any agent

The Databend Cloud skill also works outside evot. Install the complete skill directory through your agent's skill mechanism, or read its `SKILL.md` and run the included Python scripts. No MCP server or third-party Python packages are required.

Start with [databend-cloud/SKILL.md](skills/databend-cloud/SKILL.md). The metadata records the skill version and last modification date; [CHANGELOG.md](skills/databend-cloud/CHANGELOG.md) records changes. Credentials live outside the repository in separate `~/.config/databend-cloud/credentials/<api-host>.json` files (or are privately injected with a bound API origin). Pass the real Organization ID as `--org` on every query with the confirmed `--base-url`, or save it once as a named target (`cloud_config.py set-target <name> --org <ID> --base-url <origin>`, stored without secrets in `~/.config/databend-cloud/targets.json`) and pass `--target <name>`; warehouse defaults to `default`. Agents check `list-targets` before asking for an org. Both sites can coexist without replacing another site's key or switching global state. Re-running `set-key` updates only the same origin's key after valid input.

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

### evot slash commands

Skills remain available to the model by their description. To additionally register
`/skill-name` as an evot command, opt in through `SKILL.md` frontmatter:

```yaml
metadata:
  evot:
    command:
      schema_version: 1
      description: Find loopholes, judge merge readiness, and recommend fixes
      usage: /harden [changes | <target>]
      arguments: [changes, "<target>"]
```

The command name is the skill directory name; built-in command names and aliases
are reserved. Without this block there is no slash command. An empty `command: {}`
registers the name with default description and usage. `description` and `usage`
are optional single-line text (max 512 characters). Keep `description` brief:
evot shows it in command completion menus and inline beside argument hints,
both while typing the command name and after its trailing space. Supplied usage
must start with `/skill-name`. `arguments` is an optional list of up to 32
first-argument tokens (max 64 characters each). Literals such as `changes` get local Tab completion;
`<placeholders>` are hints and never inserted as literal text. Paths retain local
completion. Free-form arguments use evot's existing AI input assistance, grounded
in the declared description and usage. Invocation always loads the skill rather
than running a local handler.

New declarations use `schema_version: 1`; missing versions are legacy v0 with the
same fields. Unsupported versions or malformed declarations leave the skill
available to the model but do not register a command; the skill browser shows the
reason. Older evot releases ignore this optional metadata.

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
