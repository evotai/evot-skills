# Connection workflow

Load for first-time connection or missing credentials, not every SQL query. Scripts are relative to the installed skill root. See [Authentication](authentication.md) for private storage and [Organization selection](organizations.md) for request parameters.

## Select the site and check the key

| Site | Console | API origin |
|------|---------|------------|
| China | `https://app.databend.cn` | `https://api.databend.cn` |
| International | `https://app.databend.com` | `https://api.databend.com` |

Use the user's endpoint or the endpoint in their pasted documentation instruction. Language-specific docs already select it. Ask which site only if unknown; do not retarget an existing key based on language. Both sites can coexist in separate `credentials/<api-host>.json` files without a global connection switch.

Check Python 3 and the actual execution environment. Local files do not automatically configure a remote agent. Validate local credentials without a network probe:

```bash
python3 scripts/cloud_config.py show --base-url <confirmed-api-origin>
```

Reuse the supported private file or bound environment key. Do not display key files or search unrelated files/variables for secrets. No alias registry, org setup command, or extra configuration file is needed. Missing credentials require the short reply below, then wait.

## Short reply when the key is missing

Use the user's language and selected endpoint. Substitute the actual absolute, shell-quoted script path. Give one command, not a long analysis plan or several storage alternatives:

> First-time setup needs a Databend Cloud personal API token. Create one at `<console-url>` under **Admin → API Tokens → Access Tokens → Generate New Token**.
>
> Run this in your private terminal and paste the token. Stars and the character count confirm input. Enter shows a masked preview and saves; empty input retries. Do not send the key in chat:
>
> ```bash
> python3 <absolute-script-path> set-key --base-url <api-origin>
> ```
>
> Once saved, tell me the **Organization ID** from **Admin → Organization Profile**. I will use the `default` warehouse.

If the Organization ID is already confirmed, ask only to be told when setup is ready. Retain a different warehouse already selected. For remote agents, use that environment's private secret mechanism; do not give a local-only command that cannot configure it. Do not run an interactive prompt in a noninteractive agent session.

Manual token entry is the supported method. Re-running `set-key` updates only the same origin after valid input; empty input or cancellation leaves it unchanged. It cannot change another file's origin.

## Ask only for missing request parameters

- Reuse a confirmed **Organization ID**. A display name/email is not the ID. Pass the confirmed ID directly as `--org <Organization-ID>`; do not create another label.
- Otherwise ask for Organization ID from **Admin → Organization Profile**. Do not require an account email, new alias, or extra setup command.
- Use `default` warehouse unless a different one was selected. If inaccessible or missing, report the error and ask for an alternative; do not probe or create resources automatically.

## Verify and resume the original task

Keep org/warehouse in request arguments, not a saved registry. The agent performs verification:

```bash
python3 scripts/cloud_config.py show --org <Organization-ID> --base-url <confirmed-api-origin>
python3 scripts/query.py --org <Organization-ID> --base-url <confirmed-api-origin> "SELECT 1"
python3 scripts/query.py --org <Organization-ID> --base-url <confirmed-api-origin> "SHOW DATABASES"
```

Present the origin, org, and warehouse before first use or a change and wait for confirmation. If the current user message already explicitly confirms the target and asks to proceed, do not ask again. `show` validates only local configuration; SQL calls test actual access.

Resume the original task on successful verification. Do not make the user save an alias or run org-setup commands. An error must not change the account, org, API origin, or warehouse automatically. Switching orgs changes only the request's `--org`; switching sites selects another origin's separate key.
