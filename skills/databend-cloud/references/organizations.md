# Organization and warehouse selection

`--org` is the actual **Organization ID** shown in **Admin → Organization Profile**. It is not a user-defined alias, display name, or email. Every SQL and query-lifecycle request requires it. If a user supplies an org name, use it as `--org` only when they confirm it is the Organization ID; otherwise ask for confirmation.

## One key, multiple organizations

A personal token identifies an account. The service validates that account's active membership and role in the requested org. Reuse the same key for its organizations on the same API origin; do not duplicate the key per org or assume naming a token restricts its permissions.

```bash
python3 scripts/query.py --org acme-dev --base-url <confirmed-api-origin> "SHOW DATABASES"
python3 scripts/query.py --org acme-prod --base-url <confirmed-api-origin> "SHOW DATABASES"
```

Switching organizations changes only `--org`, not a stored mapping or a global active org. There is no alias/configuration registry, no org-setup command, and no automatic org discovery. The agent remembers confirmed request parameters in the conversation and passes them explicitly. Do not ask the user to invent another name.

## API origin and account

| Site | API origin |
|------|------------|
| China | `https://api.databend.cn` |
| International | `https://api.databend.com` |

Keep the selected origin explicit. Language-specific guides supply the endpoint; do not ask again or switch based on conversation language. The same Organization ID at two origins need not identify the same resources or account.

Keys are saved in separate `credentials/<api-host>.json` files. Selecting `--base-url` selects the matching file before any HTTP request, without modifying either site's keys. A saved key takes precedence over an unrelated environment key. A missing site's key is an error, not permission to borrow the other site's key.

Another account on the same site can use a separate private file:

```bash
python3 scripts/query.py --org acme-prod --base-url <confirmed-api-origin> \
  --credentials-file /private/work.json "SELECT 1"
```

The file's bound origin must match. See [Authentication](authentication.md) for exact precedence and private setup.

## Warehouse

Use `default` unless the user explicitly selected another warehouse:

```bash
python3 scripts/query.py --org acme-prod --base-url <confirmed-api-origin> --warehouse analytics "SELECT 1"
```

Do not ask for a warehouse as a mandatory setup field. A missing/inaccessible `default` is an error; ask for an alternative in the same org rather than probing or creating resources. Each invocation is independent; an earlier `USE WAREHOUSE` does not configure later helper calls.

## Verify and preserve target boundaries

```bash
python3 scripts/cloud_config.py show --org acme-prod --base-url <confirmed-api-origin>
```

`show` prints only endpoint, org, warehouse, and credential source. It does not verify token validity or network access. Confirm these parameters before the first query or a target change, unless the user already explicitly confirmed them. Never change accounts, orgs, or warehouses in response to an empty result or a permission error.

Warehouse listing/lifecycle operations are available through [management SQL](warehouse-management.md) with the gateway's required admin role. Console REST management and org-list APIs do not accept this personal-token authentication in the reviewed source. See [API capabilities](api-capabilities.md); do not scrape browser cookies to work around missing discovery APIs.
