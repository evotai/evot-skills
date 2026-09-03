#!/usr/bin/env python3
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

DEFAULT_HOST = "api.databend.com"
DEFAULT_WAREHOUSE = "default"
PREFIX = "BENDCLOUD_DSN"
RETRYABLE = ("ProvisionWarehouseTimeout", "ProvisionWarehouse")
USER_AGENT = "evot-databend-cloud/1"
HINT = (
    "Databend Cloud is not configured. Run in evot:\n"
    "  /env set BENDCLOUD_DSN=bendcloud://<org>:<api-token>@api.databend.com/<warehouse>"
)


class ConfigError(Exception):
    pass


class QueryError(Exception):
    pass


def parse_dsn(dsn):
    parsed = urllib.parse.urlparse(dsn)
    if parsed.scheme not in ("bendcloud", "databend"):
        raise ConfigError(f"unsupported DSN scheme: {parsed.scheme or '(none)'}")
    org = urllib.parse.unquote(parsed.username or "")
    token = urllib.parse.unquote(parsed.password or "")
    if not org or not token:
        raise ConfigError("DSN must contain both <org> and <api-token>")
    return {
        "org": org,
        "token": token,
        "host": parsed.hostname or DEFAULT_HOST,
        "port": parsed.port,
        "warehouse": parsed.path.strip("/") or DEFAULT_WAREHOUSE,
    }


def available_targets(env):
    return sorted(
        key[len(PREFIX) + 1 :]
        for key in env
        if key.startswith(PREFIX + "_") and env[key].strip()
    )


def select_dsn(env, target=None):
    if target:
        for key in (f"{PREFIX}_{target}", f"{PREFIX}_{target.upper().replace('-', '_')}"):
            if env.get(key, "").strip():
                return env[key].strip()
        targets = available_targets(env)
        listed = ", ".join(targets) if targets else "(none)"
        raise ConfigError(f"no DSN for target '{target}'. Available targets: {listed}")

    if env.get(PREFIX, "").strip():
        return env[PREFIX].strip()

    targets = available_targets(env)
    if len(targets) == 1:
        return env[f"{PREFIX}_{targets[0]}"].strip()
    if not targets:
        raise ConfigError(HINT)
    raise ConfigError(
        f"multiple targets configured; pass --target <name>. Available targets: {', '.join(targets)}"
    )


def base_url(creds):
    host = creds["host"]
    if creds["port"]:
        host = f"{host}:{creds['port']}"
    return f"https://{host}"


def request(url, headers, payload=None, timeout=60):
    data = json.dumps(payload).encode() if payload is not None else None
    sent = {**headers, "User-Agent": USER_AGENT}
    req = urllib.request.Request(url, data=data, headers=sent, method="POST" if data else "GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode() or "{}")
    except urllib.error.HTTPError as error:
        body = error.read().decode(errors="replace")
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            raise QueryError(f"HTTP {error.code}: {body.strip()[:400]}") from None
    except urllib.error.URLError as error:
        raise QueryError(f"cannot reach {url}: {error.reason}") from None


def raise_for_error(payload):
    error = payload.get("error")
    if not error:
        return
    if isinstance(error, dict):
        kind = error.get("kind") or f"code={error.get('code')}"
        raise QueryError(f"{kind}: {error.get('message', '')}".strip())
    raise QueryError(str(error))


def run_once(sql, creds, timeout):
    root = base_url(creds)
    headers = {
        "Content-Type": "application/json",
        "X-DatabendCloud-Token": creds["token"],
        "X-DatabendCloud-Org": creds["org"],
        "X-DatabendCloud-Warehouse": creds["warehouse"],
    }

    first = request(f"{root}/v1/query", headers, {"sql": sql}, timeout)
    raise_for_error(first)
    query_id = first.get("id", "")
    schema = first.get("schema", [])
    rows = list(first.get("data", []))

    next_uri = first.get("next_uri", "")
    deadline = time.monotonic() + timeout
    while next_uri and "/final" not in next_uri:
        if time.monotonic() > deadline:
            raise QueryError(f"still paging results after {timeout}s; query_id={query_id}")
        page = request(f"{root}{next_uri}", headers, None, timeout)
        raise_for_error(page)
        rows.extend(page.get("data", []))
        following = page.get("next_uri", "")
        if following == next_uri:
            time.sleep(0.2)
        next_uri = following

    if query_id:
        try:
            request(f"{root}/v1/query/{query_id}/final", headers, None, 10)
        except QueryError:
            pass
    return schema, rows


def run(sql, creds, timeout, retries=3):
    for attempt in range(retries):
        try:
            return run_once(sql, creds, timeout)
        except QueryError as error:
            last = attempt == retries - 1
            if last or not any(marker in str(error) for marker in RETRYABLE):
                raise
            wait = 5 * (attempt + 1)
            print(f"WARN: {error}; retrying in {wait}s", file=sys.stderr)
            time.sleep(wait)
    raise QueryError("exhausted retries")


def render_table(schema, rows, limit=60):
    names = [column.get("name", "?") for column in schema]
    if not rows:
        print("(0 rows)")
        return
    if any(
        "time" in column.get("name", "").lower() or "timestamp" in str(column.get("type", "")).lower()
        for column in schema
    ):
        print("(time columns are UTC)")

    text = [["NULL" if value is None else str(value) for value in row] for row in rows]
    widths = [len(name) for name in names]
    for row in text:
        for index, value in enumerate(row[: len(widths)]):
            widths[index] = max(widths[index], min(len(value), limit))

    print(" | ".join(name.ljust(widths[index]) for index, name in enumerate(names)))
    print("-+-".join("-" * width for width in widths))
    for row in text:
        cells = []
        for index, value in enumerate(row[: len(widths)]):
            shown = f"{value[: limit - 3]}..." if len(value) > limit else value
            cells.append(shown.ljust(widths[index]))
        print(" | ".join(cells))
    print(f"({len(rows)} rows)")


def main():
    parser = argparse.ArgumentParser(description="Run SQL on Databend Cloud")
    parser.add_argument("sql")
    parser.add_argument("--target")
    parser.add_argument("--warehouse")
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument("--format", choices=["table", "json"], default="table")
    args = parser.parse_args()

    try:
        creds = parse_dsn(select_dsn(os.environ, args.target))
    except ConfigError as error:
        print(error, file=sys.stderr)
        return 2

    if args.warehouse:
        creds["warehouse"] = args.warehouse

    try:
        schema, rows = run(args.sql, creds, args.timeout)
    except QueryError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    if args.format == "json":
        print(json.dumps(schema, ensure_ascii=False))
        for row in rows:
            print(json.dumps(row, ensure_ascii=False))
    else:
        render_table(schema, rows)
    return 0


if __name__ == "__main__":
    sys.exit(main())
