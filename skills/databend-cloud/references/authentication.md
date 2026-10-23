# Authentication

## Short private setup

Manual personal-token entry is the supported method. Do not invent CLI login, browser authorization, or device codes. Use the endpoint the user supplied or pasted from documentation; ask which site only when unknown. Never retarget existing credentials because the user speaks another language.

Give the matching console token-creation path and one copyable `set-key --base-url <origin>` command with the actual installed script path. The user creates and privately enters the token. The agent asks only for a missing Organization ID, passes it as `--org`, confirms the endpoint/org/warehouse, and verifies access. Warehouse defaults to `default`; no alias or additional org setup is needed.

## Credential and origin

| Site | Token-creation console | API origin |
|------|------------------------|------------|
| China | `https://app.databend.cn` | `https://api.databend.cn` |
| International | `https://app.databend.com` | `https://api.databend.com` |

Create a **personal API token**, not a SQL password, using the standalone account-token entry at the bottom of the console sidebar, outside Admin:

- International UI: **Account API Tokens → Access Tokens → Generate New Token**.
- China UI: **账户 API 令牌 → 访问令牌 → 生成新令牌**.

The token belongs to an account and accesses active org memberships subject to their roles. Token names do not restrict permissions. Revoke tokens in the console.

The API origin is HTTPS without a path suffix, not a tenant SQL gateway. Never retry a failure at another site or assume credentials/org memberships are interchangeable.

## Separate keys per origin

```text
~/.config/databend-cloud/credentials/
  api.databend.cn.json
  api.databend.com.json
```

Each private file contains a required origin and a single account key:

```json
{
  "base_url": "https://api.databend.cn",
  "api_key": "<personal-api-token>"
}
```

Org and warehouse are request arguments, not entries in another configuration file. `XDG_CONFIG_HOME` changes the credential root. `--credentials-file <path>` supports a private location or another account on the same origin. Ports are encoded in default filenames to prevent collisions.

Give only the selected site's command:

```bash
python3 scripts/cloud_config.py set-key --base-url <selected-api-origin>
```

Typing/pasting shows stars and a character count. Enter shows one masked preview (first/last four characters for long keys, fully masked short keys), then saves. Empty/invalid multi-line input retries without writing. Backspace edits, Ctrl+U clears, Ctrl+C cancels. A bracketed paste with trailing newlines waits for Enter.

Re-running `set-key` replaces only that origin's key after valid input, without another flag. Empty input, cancellation, or atomic-write failure preserves the previous file. A custom file cannot be retargeted to another origin. Origin binding is checked again under a file lock after input, so a concurrent update cannot silently change the site.

Files are written atomically with Unix mode `600`. Symlinks, wrong-owner files, and group/other-readable keys are rejected. Plain JSON is not encrypted; there is no built-in keyring. Do not display key files through agent tools, commit them, or save them in the installed skill directory.

## Environment and remote agents

A remote agent needs credentials in its actual execution environment. The user's local terminal does not configure an unrelated container or remote host.

Use host-managed secrets or a private secret-manager pipe, never chat, process arguments, shell history, or a here-document containing a key. Workflow template:

```text
<approved-secret-manager-command> | python3 scripts/cloud_config.py set-key --stdin --base-url <selected-api-origin>
```

Do not invent the user's secret-manager command. Without `--stdin`, a noninteractive session is refused rather than falling back to echoed input.

| Variable | Purpose |
|----------|---------|
| `DATABEND_CLOUD_API_KEY` | Privately injected account key, used when no selected file exists. |
| `DATABEND_CLOUD_BASE_URL` | Origin bound to the environment key; set explicitly for China. Low-level fallback is international. |
| `DATABEND_CLOUD_CREDENTIALS_FILE` | Explicit private account-file default. |

`--org` is required on every query/API call. `--warehouse` defaults to `default`. Org/warehouse aliases and implicit environment org selection are not implemented.

## Credential resolution

1. Use `--base-url`, then `DATABEND_CLOUD_BASE_URL`, then the international fallback. Onboarding and generated requests should explicitly pass the confirmed origin.
2. `--credentials-file`, then `DATABEND_CLOUD_CREDENTIALS_FILE`, selects an account file. An explicit origin must match its binding. Without an origin selection, an explicit file selects its own origin. Invalid/missing selected files never fall back to another identity.
3. Otherwise use the origin's saved file. A host's environment key must not override it, including when the file is invalid.
4. Only if that saved file is absent, use `DATABEND_CLOUD_API_KEY` bound to `DATABEND_CLOUD_BASE_URL` (international if omitted). A conflicting `--base-url` cannot forward it to another site.
5. If no key exists, stop before network requests. Do not decode unrelated connection strings, inspect other skills, or rewrite credentials to make the request work.

## Local verification

```bash
python3 scripts/cloud_config.py show --base-url <confirmed-api-origin>
python3 scripts/cloud_config.py show --org <Organization-ID> --base-url <confirmed-api-origin>
```

`show` prints only endpoint, optional org, warehouse, and credential source. An omitted org is printed as null; this allows checking the key before asking for a missing ID. It does not prove server access. Normal queries still require `--org` explicitly.
