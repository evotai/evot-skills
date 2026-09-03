# lark

Feishu / Lark skills for `lark-cli`, installed and updated as one unit.

## Why this is a group

Every `lark-*` skill starts by reading `../lark-shared/SKILL.md`, which carries the shared rules for identity (`--as user` vs `--as bot`), authentication, the JSON output contract, and the high-risk write gate. Installing a subset would leave those references dangling, so the whole directory is one install unit.

## Prerequisite

All skills here shell out to `lark-cli`:

```bash
command -v lark-cli
```

Authentication and scopes are handled by `lark-shared`, not by this file.

## Upstream

These skills are generated and maintained by `lark-cli` itself and vendored here. To refresh, copy the generated skill directories over the existing ones, then run the catalog validator from the repo root:

```bash
python3 scripts/validate.py
```

Keep the directory names unchanged: skill names are global in evot, and the cross-references between these skills are path-based.
