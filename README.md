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
| `databend-cloud` | Query and diagnose Databend | `python3`, `BENDCLOUD_DSN` |
| `humanize` | Make AI writing sound human | — |
| `lark` | Work with Feishu messages, docs, and calendars | `lark-cli` |
| `opencli` | Browse, research, and automate the web | `opencli` |

## Contributing

Each directory under `skills/` is one install unit: a single skill or a group installed together.

```text
skills/
├── humanize/
│   ├── .display.json
│   └── SKILL.md
└── lark/
    ├── .display.json
    ├── lark-im/SKILL.md
    └── lark-doc/SKILL.md
```

Follow the [Agent Skills specification](https://agentskills.io/specification). Each `SKILL.md` needs a unique `name` matching its directory and a `description` explaining when to use it. Groups cannot nest; file references must stay within the install unit.

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
      env: [BENDCLOUD_DSN]
      bins: [python3]
```

Store secrets with `/env set`, never in this repo.

## Validation

```bash
python3 scripts/validate.py
python3 -m unittest discover -s tests -v
python3 scripts/run_tests.py
```

CI checks layout, frontmatter, display metadata, references, and file safety, then runs validator and skill tests.
