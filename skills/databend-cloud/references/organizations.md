# Organization and target selection

Every SQL and query-lifecycle request needs an API origin, an **Organization ID**, and a warehouse. Supply them either directly (`--org <Organization-ID> --base-url <origin> [--warehouse <wh>]`) or through a **saved target** (`--target <name>`), which expands to those three values from a local registry.

`--org` is the actual Organization ID shown in **Admin → Organization Profile**. It is not a display name or email. If a user supplies an org name, use it as `--org` only when they confirm it is the Organization ID.

## Saved targets: resolve locally before asking

Accounts with several organizations (production tenants, a shared admin-log org, a China-site org) should not be asked for the Organization ID in every session. The registry at `~/.config/databend-cloud/targets.json` (under `XDG_CONFIG_HOME` if set) maps a short name to `base_url`, `org`, `warehouse`, and a free-text `note`. It holds no secrets; the key still comes from the origin's credential file.

```bash
python3 scripts/cloud_config.py list-targets
python3 scripts/cloud_config.py set-target acme-logs --org <Organization-ID> --base-url https://api.databend.com \
  --warehouse default --note "shared admin log org; serves tenant logs for customer Acme"
python3 scripts/cloud_config.py remove-target acme-logs
python3 scripts/query.py --target acme-logs "SHOW DATABASES"
```

Agent procedure:

1. Run `list-targets` first. Match the user's subject (customer name, tenant, workload, "admin logs", site) against target names and `note` text.
2. If exactly one target fits, state it in one line (`target=acme-logs org=… base_url=… warehouse=…`) and proceed. Do not wait for a reply unless the user asked to be consulted.
3. If several fit or none fit, ask only for what is missing: which target, or the Organization ID (plus site when unknown). After the user supplies an ID, offer a `set-target` command so the next session skips the question.
4. There is no default or active target. An omitted `--org`/`--target` is an error that lists saved target names; never pick one silently.

`--target` with an explicit `--org` or `--base-url` that disagrees with the saved entry is a configuration error; drop one of them instead of mixing. `--warehouse` may override the target's warehouse for one call. The `note` field is for humans and routing; it is not sent to the server. Record the serving warehouse in the target when the user prefers one other than `default`.

## One key, multiple organizations

A personal token identifies an account. The service validates that account's active membership and role in the requested org. Reuse the same key for its organizations on the same API origin; do not duplicate the key per org or assume naming a token restricts its permissions.

```bash
python3 scripts/query.py --org acme-dev --base-url <confirmed-api-origin> "SHOW DATABASES"
python3 scripts/query.py --org acme-prod --base-url <confirmed-api-origin> "SHOW DATABASES"
```

Switching organizations changes only `--org` or `--target`, not a global active org. Remote org discovery (listing an account's orgs) is not available with a personal token; the local registry is the only lookup.

## API origin and account

| Site | API origin |
|------|------------|
| China | `https://api.databend.cn` |
| International | `https://api.databend.com` |

Keep the selected origin explicit. Language-specific guides supply the endpoint; do not ask again or switch based on conversation language. The same Organization ID at two origins need not identify the same resources or account. A target binds one origin; save separate targets for the same customer on both sites.

Keys are saved in separate `credentials/<api-host>.json` files. Selecting `--base-url` (directly or via a target) selects the matching file before any HTTP request, without modifying either site's keys. A saved key takes precedence over an unrelated environment key. A missing site's key is an error, not permission to borrow the other site's key.

Another account on the same site can use a separate private file:

```bash
python3 scripts/query.py --org acme-prod --base-url <confirmed-api-origin> \
  --credentials-file /private/work.json "SELECT 1"
```

The file's bound origin must match. See [Authentication](authentication.md) for exact precedence and private setup.

## Warehouse

Use `default` unless the user explicitly selected another warehouse or the target records one:

```bash
python3 scripts/query.py --org acme-prod --base-url <confirmed-api-origin> --warehouse analytics "SELECT 1"
```

Do not ask for a warehouse as a mandatory setup field. A missing/inaccessible `default` is an error; ask for an alternative in the same org rather than probing or creating resources. Each invocation is independent; an earlier `USE WAREHOUSE` does not configure later helper calls.

## Verify and preserve target boundaries

```bash
python3 scripts/cloud_config.py show --target acme-logs
python3 scripts/cloud_config.py show --org acme-prod --base-url <confirmed-api-origin>
```

`show` prints only endpoint, org, warehouse, credential source, and the target name. It does not verify token validity or network access. Confirm these parameters before the first query or a target change, unless the user already explicitly confirmed them or a saved target supplied them. Never change accounts, orgs, or warehouses in response to an empty result or a permission error.

Warehouse listing/lifecycle operations are available through [management SQL](warehouse-management.md) with the gateway's required admin role. Console REST management and org-list APIs do not accept this personal-token authentication in the reviewed source. See [API capabilities](api-capabilities.md); do not scrape browser cookies to work around missing discovery APIs.
