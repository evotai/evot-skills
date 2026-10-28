#!/usr/bin/env python3
"""Offline tests for per-origin keys and explicit org/warehouse selection."""
import argparse
import contextlib
import io
import json
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest import mock

import cloud_config as config

KEY = "synthetic-config-test-key"
COM = "https://api.databend.com"
CN = "https://api.databend.cn"


class ConfigTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.env = {"XDG_CONFIG_HOME": self.temp.name}
        self.directory = Path(self.temp.name) / "databend-cloud"
        self.args = argparse.Namespace(credentials_file=None, base_url=None, org="acme", warehouse=None, target=None)

    def save(self, origin=COM, key=KEY):
        path = config.credential_path(self.args, self.env, origin)
        config.write_credentials(path, {"base_url": origin, "api_key": key})
        return path

    def resolve(self, **env):
        return config.resolve(self.args, {**self.env, **env})

    def invoke(self, argv, stdin="", extra_env=None):
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.dict(os.environ, {**self.env, **(extra_env or {})}, clear=True), \
                mock.patch("sys.stdin", io.StringIO(stdin)), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                code = config.main(argv)
            except SystemExit as error:
                code = error.code
        self.assertNotIn(KEY, out.getvalue() + err.getvalue())
        return code, out.getvalue(), err.getvalue()

    def test_default_key_and_warehouse(self):
        self.save()
        selected = self.resolve()
        self.assertEqual((selected["base_url"], selected["org"], selected["warehouse"]), (COM, "acme", "default"))
        self.assertEqual(selected["api_key"], KEY)
        self.assertEqual(set(selected), {"base_url", "org", "warehouse", "api_key", "credential_source", "target"})
        self.assertIsNone(selected["target"])

    def test_same_key_supports_several_explicit_orgs(self):
        self.save()
        for org in ("first-org", "second-org"):
            self.args.org = org
            self.assertEqual(self.resolve()["org"], org)
            self.assertEqual(self.resolve()["api_key"], KEY)

    def test_org_required_even_if_host_has_org_or_alias_defaults(self):
        self.save()
        self.args.org = None
        with self.assertRaisesRegex(config.ConfigError, "pass --org"):
            self.resolve(DATABEND_CLOUD_ORG="ambient", DATABEND_CLOUD_CONTEXT="old-alias")

    def test_warehouse_is_explicit_or_default(self):
        self.save()
        self.assertEqual(self.resolve(DATABEND_CLOUD_WAREHOUSE="ambient")["warehouse"], "default")
        self.args.warehouse = "analytics"
        self.assertEqual(self.resolve()["warehouse"], "analytics")

    def test_missing_key_has_portable_hint(self):
        with self.assertRaisesRegex(config.ConfigError, "set-key") as raised:
            self.resolve()
        self.assertNotIn("/env", str(raised.exception))

    def test_show_checks_credentials_without_requiring_org(self):
        code, _, error = self.invoke(["show"])
        self.assertEqual(code, 2)
        self.assertIn("set-key", error)
        self.save()
        code, out, _ = self.invoke(["show"])
        self.assertEqual(code, 0)
        self.assertIsNone(json.loads(out)["org"])

    def test_show_with_org_outputs_only_safe_fields(self):
        self.save()
        code, out, _ = self.invoke(["show", "--org", "acme"])
        self.assertEqual(code, 0)
        self.assertEqual(set(json.loads(out)), {"base_url", "org", "warehouse", "credential_source", "target"})

    def test_no_context_commands_or_options(self):
        for argv in (["set-context", "x", "--org", "acme"], ["list-contexts"],
                     ["show", "--context", "x"], ["show", "--config-file", "x"]):
            self.assertEqual(self.invoke(argv)[0], 2)

    def test_unrelated_config_files_are_never_read(self):
        self.save()
        (self.directory / "config.json").write_text("not-json")
        self.assertEqual(self.resolve(DATABEND_CLOUD_CONTEXT="unused", DATABEND_CLOUD_CONFIG_FILE="missing")["org"], "acme")

    def set_target(self, name="avia", org="org-synthetic", origin=COM, warehouse=None, note=None):
        argv = ["set-target", name, "--org", org, "--base-url", origin]
        if warehouse:
            argv += ["--warehouse", warehouse]
        if note:
            argv += ["--note", note]
        return self.invoke(argv)

    def test_set_and_list_targets_without_secrets(self):
        self.save()
        code, out, _ = self.set_target(note="shared admin logs")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["org"], "org-synthetic")
        code, out, _ = self.set_target("cn-prod", "org-cn", CN, "analytics")
        self.assertEqual(code, 0)
        code, out, _ = self.invoke(["list-targets"])
        self.assertEqual(code, 0)
        listed = json.loads(out)
        self.assertEqual(sorted(listed["targets"]), ["avia", "cn-prod"])
        self.assertEqual(listed["targets"]["cn-prod"], {"base_url": CN, "org": "org-cn", "warehouse": "analytics", "note": ""})
        self.assertEqual(listed["targets"]["avia"]["note"], "shared admin logs")
        raw = (self.directory / "targets.json").read_text()
        self.assertNotIn(KEY, raw)
        self.assertEqual(json.loads(raw)["schema"], 1)

    def test_target_expands_to_origin_org_and_warehouse(self):
        self.save(CN, "china-test-key")
        self.set_target("cn-prod", "org-cn", CN, "analytics")
        self.args.org, self.args.target = None, "cn-prod"
        selected = self.resolve()
        self.assertEqual((selected["base_url"], selected["org"], selected["warehouse"], selected["target"]),
                         (CN, "org-cn", "analytics", "cn-prod"))
        self.assertEqual(selected["api_key"], "china-test-key")
        self.args.warehouse = "override"
        self.assertEqual(self.resolve()["warehouse"], "override")

    def test_target_conflicts_with_explicit_org_or_origin(self):
        self.save()
        self.set_target()
        self.args.target = "avia"
        self.args.org = "other-org"
        with self.assertRaisesRegex(config.ConfigError, "conflicts with target"):
            self.resolve()
        self.args.org, self.args.base_url = "org-synthetic", CN
        with self.assertRaisesRegex(config.ConfigError, "conflicts with target"):
            self.resolve()
        self.args.base_url = COM
        self.assertEqual(self.resolve()["org"], "org-synthetic")

    def test_unknown_target_and_missing_org_list_saved_targets(self):
        self.save()
        self.set_target()
        self.args.target = "missing"
        with self.assertRaisesRegex(config.ConfigError, "Unknown target 'missing'.*avia"):
            self.resolve()
        self.args.target, self.args.org = None, None
        with self.assertRaisesRegex(config.ConfigError, "Saved targets.*avia"):
            self.resolve()
        self.assertEqual(self.invoke(["remove-target", "avia"])[0], 0)
        self.assertEqual(self.invoke(["remove-target", "avia"])[0], 2)
        with self.assertRaisesRegex(config.ConfigError, "No saved targets"):
            self.resolve()

    def test_target_registry_rejects_bad_schema_and_entries(self):
        self.save()
        path = self.directory / "targets.json"
        for payload in ("not-json", json.dumps({"schema": 2, "targets": {}}), json.dumps({"targets": []}),
                        json.dumps({"targets": {"x": {"org": "acme"}}}), json.dumps({"targets": {"bad name": {"org": "a", "base_url": COM}}})):
            path.write_text(payload)
            self.args.target = "x"
            with self.assertRaises(config.ConfigError):
                self.resolve()
        path.write_text(json.dumps({"targets": {"legacy": {"org": "acme", "base_url": COM}}}))
        self.args.target = "legacy"
        self.assertEqual(self.resolve()["warehouse"], "default")

    def test_set_target_requires_credentials_only_at_query_time(self):
        self.assertEqual(self.set_target()[0], 0)
        self.args.org, self.args.target = None, "avia"
        with self.assertRaisesRegex(config.ConfigError, "set-key"):
            self.resolve()

    @unittest.skipUnless(os.name == "posix", "POSIX permissions")
    def test_private_file_and_directory_permissions(self):
        path = self.save()
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(path.parent.stat().st_mode), 0o700)
        path.chmod(0o644)
        with self.assertRaisesRegex(config.ConfigError, "600"):
            self.resolve()

    def test_symlink_read_and_write_are_refused(self):
        path = self.save()
        link = self.directory / "link.json"
        link.symlink_to(path)
        self.args.credentials_file = str(link)
        with self.assertRaisesRegex(config.ConfigError, "symlink"):
            self.resolve()
        with self.assertRaises(config.ConfigError):
            config.write_credentials(link, {"api_key": "replacement"})
        self.assertEqual(json.loads(path.read_text())["api_key"], KEY)

    def test_malformed_json_does_not_echo_secret(self):
        path = self.save()
        path.write_text('{"api_key":"' + KEY)
        with self.assertRaises(config.ConfigError) as raised:
            self.resolve()
        self.assertNotIn(KEY, str(raised.exception))

    def test_invalid_credential_shape(self):
        path = self.save()
        for value in ([KEY], {"api_key": KEY}, {"base_url": COM, "api_key": ""}):
            path.write_text(json.dumps(value))
            with self.assertRaises(config.ConfigError):
                self.resolve()

    def test_bad_header_fields(self):
        self.save()
        self.args.org = "org\r\nInjected: yes"
        with self.assertRaises(config.ConfigError):
            self.resolve()
        self.args.org, self.args.warehouse = "acme", "wh\nInjected"
        with self.assertRaises(config.ConfigError):
            self.resolve()

    def test_url_normalization_and_validation(self):
        self.assertEqual(config.normalize_base_url("https://API.DATABEND.COM:443/"), COM)
        self.assertEqual(config.normalize_base_url("https://[::1]:443"), "https://[::1]")
        for url in ("http://api.example", "https://user:secret@api.example", "https://api.example/path",
                    "https://api.example?secret", "https://api.example#fragment", "https://api.example:bad", ""):
            with self.assertRaises(config.ConfigError) as raised:
                config.normalize_base_url(url)
            self.assertNotIn("secret", str(raised.exception))

    def test_relative_xdg_rejected_and_ports_have_distinct_paths(self):
        with self.assertRaises(config.ConfigError):
            config.config_dir({"XDG_CONFIG_HOME": "relative"})
        paths = [config.credential_path(self.args, self.env, f"https://api.example:{port}") for port in (8443, 9443)]
        self.assertNotEqual(*paths)
        self.assertEqual(paths[0].parent, self.directory / "credentials")

    def test_both_sites_keep_separate_keys(self):
        global_path, china_path = self.save(), self.save(CN, "china-test-key")
        before = {p: p.read_bytes() for p in (global_path, china_path)}
        for origin, key in ((CN, "china-test-key"), (COM, KEY)):
            self.args.base_url = origin
            self.assertEqual(self.resolve()["api_key"], key)
        self.assertEqual({p: p.read_bytes() for p in before}, before)

    def test_explicit_origin_prefers_own_file_over_ambient_key(self):
        self.save(CN, "china-test-key")
        self.args.base_url = CN
        selected = self.resolve(DATABEND_CLOUD_API_KEY="unrelated-key", DATABEND_CLOUD_BASE_URL=COM)
        self.assertEqual((selected["base_url"], selected["api_key"]), (CN, "china-test-key"))

    def test_mismatched_environment_key_cannot_be_forwarded(self):
        self.args.base_url = CN
        with self.assertRaisesRegex(config.ConfigError, "bound"):
            self.resolve(DATABEND_CLOUD_API_KEY="unrelated-key", DATABEND_CLOUD_BASE_URL=COM)

    def test_missing_china_key_does_not_borrow_international_file(self):
        self.save()
        self.args.base_url = CN
        with self.assertRaisesRegex(config.ConfigError, "missing"):
            self.resolve()

    def test_environment_key_is_supported_when_no_saved_key_exists(self):
        selected = self.resolve(DATABEND_CLOUD_API_KEY=KEY, DATABEND_CLOUD_BASE_URL=CN)
        self.assertEqual((selected["base_url"], selected["credential_source"]), (CN, "environment"))

    def test_saved_key_wins_over_ambient_key_and_bad_file_never_falls_back(self):
        path = self.save()
        self.assertEqual(self.resolve(DATABEND_CLOUD_API_KEY="ambient")["api_key"], KEY)
        path.write_text("broken-json")
        with self.assertRaises(config.ConfigError):
            self.resolve(DATABEND_CLOUD_API_KEY="ambient")

    def test_explicit_file_selects_account_and_origin(self):
        path = self.save(CN)
        self.args.credentials_file = str(path)
        selected = self.resolve(DATABEND_CLOUD_API_KEY="ambient")
        self.assertEqual((selected["base_url"], selected["api_key"]), (CN, KEY))
        self.args.base_url = COM
        with self.assertRaisesRegex(config.ConfigError, "bound"):
            self.resolve()

    def test_environment_file_has_priority_over_environment_key(self):
        path = self.save()
        selected = self.resolve(DATABEND_CLOUD_CREDENTIALS_FILE=str(path), DATABEND_CLOUD_API_KEY="ambient")
        self.assertEqual(selected["api_key"], KEY)
        with self.assertRaises(config.ConfigError):
            self.resolve(DATABEND_CLOUD_CREDENTIALS_FILE=str(path.with_name("missing.json")), DATABEND_CLOUD_API_KEY=KEY)

    def test_locale_does_not_retarget_credentials(self):
        self.save()
        self.assertEqual(self.resolve(LANG="zh_CN.UTF-8", LC_ALL="zh_CN.UTF-8")["base_url"], COM)

    def test_atomic_write_failure_preserves_previous_key(self):
        path = self.save()
        before = path.read_bytes()
        with mock.patch.object(config.os, "replace", side_effect=OSError("simulated failure")):
            with self.assertRaises(config.ConfigError):
                config.write_credentials(path, {"base_url": COM, "api_key": "replacement"})
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(list(path.parent.glob(".databend-*")), [])

    def test_private_stdin_setup_and_repeated_update(self):
        self.assertEqual(self.invoke(["set-key", "--stdin"], "previous-synthetic-key")[0], 0)
        self.assertEqual(self.invoke(["set-key", "--stdin"], KEY)[0], 0)
        self.assertEqual(self.resolve()["api_key"], KEY)

    def test_empty_stdin_preserves_existing_or_missing_file(self):
        for value in ("", "\n", "   \r\n"):
            self.assertEqual(self.invoke(["set-key", "--stdin"], value)[0], 2)
        path = config.credential_path(self.args, self.env, COM)
        self.assertFalse(path.exists())
        path = self.save()
        before = path.read_bytes()
        self.assertEqual(self.invoke(["set-key", "--stdin"], "\n")[0], 2)
        self.assertEqual(path.read_bytes(), before)

    def test_masked_input_never_falls_back_to_echoed_stdin(self):
        code, _, error = self.invoke(["set-key"])
        self.assertEqual(code, 2)
        self.assertIn("private interactive terminal", error)

    def test_setting_china_key_does_not_replace_international_key(self):
        path = self.save()
        before = path.read_bytes()
        self.assertEqual(self.invoke(["set-key", "--stdin", "--base-url", CN], "china-test-key")[0], 0)
        self.assertEqual(path.read_bytes(), before)
        self.args.base_url = CN
        self.assertEqual(self.resolve()["api_key"], "china-test-key")

    def test_setup_does_not_overwrite_ambient_account_file(self):
        path = self.save()
        before = path.read_bytes()
        self.assertEqual(self.invoke(["set-key", "--stdin", "--base-url", CN], "china-test-key",
                                     {"DATABEND_CLOUD_CREDENTIALS_FILE": str(path)})[0], 0)
        self.assertEqual(path.read_bytes(), before)

    def test_explicit_origin_beats_environment_on_setup(self):
        self.assertEqual(self.invoke(["set-key", "--stdin", "--base-url", COM], KEY,
                                     {"DATABEND_CLOUD_BASE_URL": CN})[0], 0)
        self.assertEqual(self.resolve()["base_url"], COM)

    def test_setup_can_use_private_environment_origin(self):
        self.assertEqual(self.invoke(["set-key", "--stdin"], KEY, {"DATABEND_CLOUD_BASE_URL": CN})[0], 0)
        self.args.base_url = CN
        self.assertEqual(self.resolve()["base_url"], CN)

    def test_custom_file_cannot_be_changed_to_another_origin(self):
        path = self.save()
        before = path.read_bytes()
        self.assertEqual(self.invoke(["set-key", "--stdin", "--base-url", CN, "--credentials-file", str(path)], "china-key")[0], 2)
        self.assertEqual(path.read_bytes(), before)

    def test_update_rechecks_origin_after_input(self):
        path = self.save()

        @contextlib.contextmanager
        def race(_path):
            config.write_credentials(path, {"base_url": CN, "api_key": "other-site-key"})
            yield

        with mock.patch.object(config, "credential_update", race):
            code, _, _ = self.invoke(["set-key", "--stdin"], KEY)
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(path.read_text())["api_key"], "other-site-key")


if __name__ == "__main__":
    unittest.main(verbosity=2)
