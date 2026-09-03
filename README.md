# evot-skills

Official skill catalog for [evot](https://github.com/evotai/evot).

## Install

```
/skill install                  # every unit in this repo
/skill install databend-cloud   # one unit
/skill update                   # refresh what is installed
```

Units land in `~/.evotai/skills/`, keeping the layout below. `/skill install` overwrites local edits, so treat installed copies as managed files.

## Catalog

| Unit | Skills | Needs |
| --- | --- | --- |
| `databend-cloud` | 1 | `python3`, `BENDCLOUD_DSN` |
| `humanize` | 1 | — |
| `lark` | 27 | `lark-cli` |
| `opencli` | 1 | `opencli` |

## Layout

```
skills/
├── databend-cloud/       unit with a SKILL.md — one skill
│   ├── SKILL.md
│   └── scripts/query.py
└── lark/                 unit without a SKILL.md — a group of skills
    ├── README.md
    ├── lark-shared/
    └── lark-im/
```

A directory under `skills/` is one install unit:

- it has a `SKILL.md`, so the unit is a single skill, or
- it has none, so every child holding a `SKILL.md` is a skill and the directory is a group.

Groups exist because skills can reference siblings — every `lark-*` skill reads `../lark-shared/SKILL.md` — so the group installs and updates as one piece. Nesting stops there; a group cannot contain another group.

Skill names are global in evot, so every name in this repo must be unique.

## Skill format

Skills follow the [Agent Skills specification](https://agentskills.io/specification): a directory with `SKILL.md`, plus optional `scripts/`, `references/`, and `assets/`. `name` must equal the directory name; `description` states what the skill does and when to use it.

Declare runtime prerequisites so `/skill install` can check them and tell the user what is missing:

```yaml
metadata:
  evot:
    requires:
      env: [BENDCLOUD_DSN]
      bins: [python3]
    envHints:
      BENDCLOUD_DSN: bendcloud://<org>:<api-token>@api.databend.com/<warehouse>
```

`envHints` supplies the value template evot shows in its `/env set` suggestion. The older `metadata.requires.bins` shape is also read.

Secrets belong in evot variables (`/env set`), never in this repo.

## Validate

```bash
python3 scripts/validate.py
```

CI runs this on every push and pull request. It checks unit layout and nesting depth, frontmatter, name uniqueness, that references resolve inside their unit, and that no symlinks, `.env` files, or oversized files are committed.
