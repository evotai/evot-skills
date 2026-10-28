#!/usr/bin/env python3
"""Private per-origin API keys plus a local registry of named targets (origin + org + warehouse)."""
import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
import re
import stat
import sys
import tempfile
import time
import urllib.parse

import secret_input

DEFAULT_BASE_URL = "https://api.databend.com"
NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")


class ConfigError(Exception):
    pass


def normalize_base_url(value):
    try:
        parsed = urllib.parse.urlsplit(value)
        port = parsed.port
        if (parsed.scheme != "https" or not parsed.hostname or parsed.username is not None
                or parsed.password is not None or parsed.path not in ("", "/")
                or parsed.query or parsed.fragment or any(c.isspace() for c in value)):
            raise ValueError
        host = parsed.hostname.lower()
        if ":" in host:
            host = f"[{host}]"
        return f"https://{host}" + (f":{port}" if port and port != 443 else "")
    except (ValueError, TypeError):
        raise ConfigError("Base URL must be an HTTPS origin, without credentials, path, query, or fragment") from None


def config_dir(env):
    root = env.get("XDG_CONFIG_HOME")
    if root and not Path(root).is_absolute():
        raise ConfigError("XDG_CONFIG_HOME must be an absolute path")
    return (Path(root) if root else Path.home() / ".config") / "databend-cloud"


def credential_path(args, env, base_url, use_environment_file=True):
    selected = (getattr(args, "credentials_file", None)
                or (env.get("DATABEND_CLOUD_CREDENTIALS_FILE") if use_environment_file else None))
    if selected:
        return Path(selected).expanduser()
    origin = normalize_base_url(base_url)
    filename = urllib.parse.quote(urllib.parse.urlsplit(origin).netloc, safe=".-") + ".json"
    return config_dir(env) / "credentials" / filename


def read_credentials(path):
    """Never expose contents or follow a credential symlink."""
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    try:
        if path.is_symlink():
            raise ConfigError("Credential file must not be a symlink")
        fd = os.open(path, flags)
    except FileNotFoundError:
        raise ConfigError("Credential file is missing for the selected API origin; run cloud_config.py set-key --base-url <origin> or privately configure an environment key for this origin") from None
    except OSError:
        raise ConfigError("Cannot open credential file; check its path and permissions") from None
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_size > 1024 * 1024:
            raise ConfigError("Credentials must be a regular JSON file smaller than 1 MiB")
        if os.name == "posix" and (info.st_uid != os.getuid() or info.st_mode & 0o077):
            raise ConfigError("Credential file must belong to you and have mode 600; fix its permissions privately")
        with os.fdopen(fd, encoding="utf-8") as stream:
            fd = None
            data = json.load(stream)
        if not isinstance(data, dict):
            raise ValueError
        return data
    except (ValueError, UnicodeError, OSError):
        raise ConfigError("Credential file is not a valid JSON object; inspect it privately") from None
    finally:
        if fd is not None:
            os.close(fd)


def write_credentials(path, data):
    try:
        path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
        if path.is_symlink() or (path.exists() and not path.is_file()):
            raise ConfigError("Refusing to replace a symlink or non-regular credential file")
        fd, temporary = tempfile.mkstemp(prefix=".databend-", dir=path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                json.dump(data, stream, indent=2)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
    except OSError:
        raise ConfigError("Cannot save credentials; check directory permissions") from None


@contextmanager
def credential_update(path, timeout=3):
    """Serialize same-origin updates without holding a lock during user input."""
    lock = path.with_name(path.name + ".lock")
    deadline = time.monotonic() + timeout
    try:
        path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
        while True:
            try:
                fd = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                break
            except FileExistsError:
                if time.monotonic() >= deadline:
                    raise ConfigError("Credentials are locked; retry later. Do not remove another process's lock") from None
                time.sleep(0.05)
    except OSError:
        raise ConfigError("Cannot lock credentials; check directory permissions") from None
    try:
        yield
    finally:
        os.close(fd)
        lock.unlink()


def identifier(value, label):
    if not isinstance(value, str) or not NAME.fullmatch(value):
        raise ConfigError(f"{label} must use letters, digits, dots, underscores, or hyphens (maximum 128 characters)")
    return value


def api_key(value):
    try:
        return secret_input.validate_key(value)
    except secret_input.InputError as error:
        raise ConfigError(str(error)) from None


def credential_origin(saved):
    if not saved.get("base_url"):
        raise ConfigError("Credential file needs an explicit base_url; configure it privately for the intended origin")
    return normalize_base_url(saved["base_url"])


TARGETS_SCHEMA = 1


def targets_path(env):
    return config_dir(env) / "targets.json"


def read_targets(env):
    """Named targets hold no secrets; a missing file is an empty registry."""
    path = targets_path(env)
    try:
        if not path.exists():
            return {}
        if path.stat().st_size > 1024 * 1024:
            raise ValueError
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeError):
        raise ConfigError(f"Target registry {path} is not valid JSON; fix or remove it") from None
    if not isinstance(data, dict) or not isinstance(data.get("targets"), dict):
        raise ConfigError(f"Target registry {path} must be an object with a \"targets\" map")
    if data.get("schema", TARGETS_SCHEMA) != TARGETS_SCHEMA:
        raise ConfigError(f"Target registry {path} uses unsupported schema {data.get('schema')!r}")
    targets = {}
    for name, entry in data["targets"].items():
        if not isinstance(entry, dict) or not entry.get("org") or not entry.get("base_url"):
            raise ConfigError(f"Target {name!r} must have org and base_url; run set-target again")
        targets[identifier(name, "Target name")] = {
            "base_url": normalize_base_url(entry["base_url"]),
            "org": identifier(entry["org"], "Organization ID"),
            "warehouse": identifier(entry.get("warehouse") or "default", "Warehouse"),
            "note": str(entry.get("note") or "")[:200],
        }
    return targets


def write_targets(env, targets):
    path = targets_path(env)
    payload = {"schema": TARGETS_SCHEMA, "targets": {name: dict(targets[name]) for name in sorted(targets)}}
    try:
        path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
        if path.is_symlink():
            raise ConfigError("Refusing to replace a symlinked target registry")
        fd, temporary = tempfile.mkstemp(prefix=".targets-", dir=path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                json.dump(payload, stream, indent=2, ensure_ascii=False)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
    except OSError:
        raise ConfigError("Cannot save target registry; check directory permissions") from None


def target_hint(env):
    try:
        names = sorted(read_targets(env))
    except ConfigError:
        return ""
    if not names:
        return " No saved targets; save one with cloud_config.py set-target <name> --org <Organization-ID> --base-url <origin>"
    return " Saved targets (use --target <name>): " + ", ".join(names)


def apply_target(args, env):
    """Expand --target into origin/org/warehouse; explicit flags must agree with the saved target."""
    name = getattr(args, "target", None)
    if not name:
        return None
    targets = read_targets(env)
    if name not in targets:
        raise ConfigError(f"Unknown target {name!r}.{target_hint(env)}")
    target = targets[name]
    for field in ("org", "base_url"):
        given = getattr(args, field, None)
        if given and (normalize_base_url(given) if field == "base_url" else given) != target[field]:
            raise ConfigError(f"--{field.replace('_', '-')} {given!r} conflicts with target {name!r} ({target[field]}); drop one of them")
        setattr(args, field, target[field])
    if not getattr(args, "warehouse", None):
        args.warehouse = target["warehouse"]
    return target


def resolve(args, env, require_org=True):
    target = apply_target(args, env)
    org = getattr(args, "org", None)
    if not org and require_org:
        raise ConfigError("Organization is required; pass --org <Organization-ID> or --target <saved-name>. Never guess the organization." + target_hint(env))
    if org is not None:
        org = identifier(org, "Organization ID")
    selected_origin = getattr(args, "base_url", None) or env.get("DATABEND_CLOUD_BASE_URL")
    root = normalize_base_url(selected_origin or DEFAULT_BASE_URL)
    explicit_file = getattr(args, "credentials_file", None) or env.get("DATABEND_CLOUD_CREDENTIALS_FILE")
    path = credential_path(args, env, root)
    # A site's saved key wins over an unrelated host-injected identity.
    if explicit_file or path.exists() or path.is_symlink() or not env.get("DATABEND_CLOUD_API_KEY"):
        saved = read_credentials(path)
        saved_origin = credential_origin(saved)
        if (selected_origin and saved_origin != root) or (not explicit_file and saved_origin != root):
            raise ConfigError("Credential file is bound to another Base URL; select a separate credential file for the intended origin")
        root, token, source = saved_origin, api_key(saved.get("api_key")), "file"
    else:
        bound_origin = normalize_base_url(env.get("DATABEND_CLOUD_BASE_URL") or DEFAULT_BASE_URL)
        if root != bound_origin:
            raise ConfigError("Environment API key is bound to another Base URL; configure a key for the selected origin")
        token, source = api_key(env["DATABEND_CLOUD_API_KEY"]), "environment"
    warehouse = getattr(args, "warehouse", None) or "default"
    return {"base_url": root, "api_key": token, "org": org,
            "warehouse": identifier(warehouse, "Warehouse"), "credential_source": source,
            "target": getattr(args, "target", None) if target else None}


def add_options(parser, require_org=True):
    parser.add_argument("--org", help="Organization ID, not a display name or local alias")
    parser.add_argument("--target", help="Saved target name from cloud_config.py list-targets (supplies origin, org, warehouse)")
    parser.add_argument("--base-url", help="HTTPS API origin; must match the credential")
    parser.add_argument("--warehouse", help="Warehouse name (default: default, or the target's warehouse)")
    parser.add_argument("--credentials-file", help="Explicit private account credential JSON file")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Configure per-origin Databend Cloud API keys and named targets")
    commands = parser.add_subparsers(dest="command", required=True)
    key = commands.add_parser("set-key", help="Privately set/update the key for one API origin")
    key.add_argument("--credentials-file")
    key.add_argument("--base-url")
    key.add_argument("--stdin", action="store_true", help="Read from a secret-manager pipe, not a command argument")
    show = commands.add_parser("show", help="Validate local credentials and optional org/warehouse without a network call")
    add_options(show, require_org=False)
    set_target = commands.add_parser("set-target", help="Save or update a named target (origin + org + warehouse; no secrets)")
    set_target.add_argument("name")
    set_target.add_argument("--org", required=True, help="Organization ID from Admin → Organization Profile")
    set_target.add_argument("--base-url", required=True, help="HTTPS API origin for this target")
    set_target.add_argument("--warehouse", default="default")
    set_target.add_argument("--note", default="", help="Short human description, e.g. which workloads or tenants it serves")
    remove_target = commands.add_parser("remove-target", help="Delete a named target")
    remove_target.add_argument("name")
    commands.add_parser("list-targets", help="Print saved targets as JSON")
    args = parser.parse_args(argv)
    try:
        if args.command == "set-key":
            root = normalize_base_url(args.base_url or os.environ.get("DATABEND_CLOUD_BASE_URL") or DEFAULT_BASE_URL)
            path = credential_path(args, os.environ, root, use_environment_file=False)
            if path.exists() or path.is_symlink():
                if credential_origin(read_credentials(path)) != root:
                    raise ConfigError("Cannot replace another origin's key; use a separate credential file")
            if not args.stdin and not sys.stdin.isatty():
                raise ConfigError("Use a private interactive terminal for masked input, or --stdin with a secret-manager pipe")
            token = (sys.stdin.read(secret_input.MAX_KEY_LENGTH + 2).strip() if args.stdin else secret_input.read_key())
            token = api_key(token)
            with credential_update(path):
                if path.exists() or path.is_symlink():
                    if credential_origin(read_credentials(path)) != root:
                        raise ConfigError("Cannot replace another origin's key; use a separate credential file")
                write_credentials(path, {"base_url": root, "api_key": token})
            print(f"Credential saved privately for {root}. No connection was attempted.")
        elif args.command == "set-target":
            name = identifier(args.name, "Target name")
            targets = read_targets(os.environ)
            targets[name] = {"base_url": normalize_base_url(args.base_url), "org": identifier(args.org, "Organization ID"),
                             "warehouse": identifier(args.warehouse, "Warehouse"), "note": args.note[:200]}
            write_targets(os.environ, targets)
            print(json.dumps({"target": name, **targets[name]}, indent=2, ensure_ascii=False))
        elif args.command == "remove-target":
            targets = read_targets(os.environ)
            if args.name not in targets:
                raise ConfigError(f"Unknown target {args.name!r}.{target_hint(os.environ)}")
            del targets[args.name]
            write_targets(os.environ, targets)
            print(f"Removed target {args.name}")
        elif args.command == "list-targets":
            targets = read_targets(os.environ)
            print(json.dumps({"path": str(targets_path(os.environ)), "targets": targets}, indent=2, ensure_ascii=False))
        else:
            selected = resolve(args, os.environ, require_org=False)
            print(json.dumps({field: selected[field] for field in
                              ("base_url", "org", "warehouse", "credential_source", "target")}, indent=2))
        return 0
    except (ConfigError, secret_input.InputError, EOFError, KeyboardInterrupt) as error:
        print(str(error) or "Configuration cancelled", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
