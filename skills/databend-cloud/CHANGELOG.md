# Changelog

Versions here identify the skill, not a Databend Cloud server release. Dates are UTC.

## 1.1.0 — 2026-10-28

- Add a local named-target registry (`cloud_config.py set-target / list-targets / remove-target`, `~/.config/databend-cloud/targets.json`). A target stores origin, Organization ID, warehouse, and a routing note; it never stores a key.
- `query.py`, `query_api.py`, and `cloud_config.py show` accept `--target <name>` as an alternative to `--org/--base-url`. Explicit flags that disagree with the target are errors; `--warehouse` may override per call.
- Agents must run `list-targets` and match the subject before asking for an Organization ID, and should offer `set-target` after a user supplies one. There is still no default or active target; a missing `--org/--target` error lists saved names.

## 1.0.1 — 2026-10-23

- Update token creation guidance to the standalone **Account API Tokens** sidebar entry.
- Use **账户 API 令牌 → 访问令牌 → 生成新令牌** for the China console.

## 1.0.0 — 2026-10-19

First explicitly versioned skill revision. Local changes are not a published repository release until committed and released.

- Use the actual Organization ID via required `--org` on every query/API request. No alias registry, saved org configuration, or compatibility commands.
- Keep account credentials separate by API origin; both Cloud sites can coexist. Warehouse defaults to `default` unless explicitly selected.
- Preserve masked terminal input, safe same-origin key updates, bounded query lifecycle helpers, personal-token API references, and SQL documentation discovery.
- Use one short entrypoint; load incident workflows, log schema, memory analysis, recipes, and exports from references only when needed.
- Keep tests offline and fixtures synthetic; do not include production account or organization identifiers.
