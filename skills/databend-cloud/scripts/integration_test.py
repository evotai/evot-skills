#!/usr/bin/env python3
"""Standalone offline org requests, dual sites, and independent key updates."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
KEY = "synthetic-integration-key"
COM = "https://api.databend.com"
CN = "https://api.databend.cn"


class StandaloneTest(unittest.TestCase):
    def environment(self, root):
        env = {key: value for key, value in os.environ.items() if key in ("PATH", "SYSTEMROOT", "WINDIR")}
        env.update({"HOME": str(root), "XDG_CONFIG_HOME": str(root / "config")})
        return env

    def configure(self, scripts, env, origin, key):
        result = subprocess.run([sys.executable, str(scripts / "cloud_config.py"), "set-key", "--stdin", "--base-url", origin],
                                input=key, capture_output=True, text=True, env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn(key, result.stdout + result.stderr)

    def test_installed_scripts_need_only_key_and_org_from_unrelated_directory(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            install = root / "installed-skill/scripts"
            install.mkdir(parents=True)
            for name in ("query.py", "query_api.py", "cloud_config.py", "secret_input.py"):
                shutil.copyfile(HERE / name, install / name)
            env = self.environment(root)
            self.configure(install, env, COM, KEY)
            result = subprocess.run([sys.executable, str(install / "cloud_config.py"), "show", "--org", "acme-prod"],
                                    capture_output=True, text=True, env=env, cwd=root)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["warehouse"], "default")
            harness = """
import sys
sys.path.insert(0, sys.argv[1])
import query, query_api
calls = []
def request(url, headers, payload=None, timeout=60):
    calls.append(url)
    assert headers['X-DatabendCloud-Org'] == sys.argv[2]
    assert headers['X-DatabendCloud-Warehouse'] == 'default'
    assert headers['X-DatabendCloud-Token']
    if url.endswith('/query'):
        return {'id': 'q', 'schema': [{'name': 'ok'}], 'data': [[1]], 'next_uri': '/v1/query/q/final'}
    return {}
query.request = request
assert query.main(['--org', sys.argv[2], '--format', 'json', 'SELECT 1']) == 0
assert query_api.main(['status', 'q', '--org', sys.argv[2]]) == 0
assert len(calls) == 3
"""
            for org in ("acme-dev", "acme-prod"):
                result = subprocess.run([sys.executable, "-c", harness, str(install), org],
                                        capture_output=True, text=True, env=env, cwd=root)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertNotIn(KEY, result.stdout + result.stderr)
                self.assertEqual(json.loads(result.stdout.splitlines()[1]), [1])
            self.assertFalse((root / "config/databend-cloud/config.json").exists())

    def test_both_sites_same_org_without_changing_files_or_global_state(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            env = self.environment(root)
            for label, origin in (("global", COM), ("china", CN)):
                self.configure(HERE, env, origin, f"synthetic-{label}-key")
            files = list((root / "config/databend-cloud").rglob("*.json"))
            before = {path: path.read_bytes() for path in files}
            harness = """
import sys
sys.path.insert(0, sys.argv[1])
import query
origin = {'global': 'https://api.databend.com', 'china': 'https://api.databend.cn'}[sys.argv[2]]
def request(url, headers, payload=None, timeout=60):
    assert url.startswith(origin + '/v1/query')
    assert headers['X-DatabendCloud-Token'] == 'synthetic-' + sys.argv[2] + '-key'
    assert headers['X-DatabendCloud-Org'] == 'same-org'
    if url.endswith('/query'):
        return {'id': 'q', 'schema': [{'name': 'ok'}], 'data': [[1]], 'next_uri': '/v1/query/q/final'}
    return {}
query.request = request
raise SystemExit(query.main(['--base-url', origin, '--org', 'same-org', 'SELECT 1']))
"""
            env.update({"DATABEND_CLOUD_API_KEY": "unrelated-ambient-key", "DATABEND_CLOUD_BASE_URL": COM})
            processes = [subprocess.Popen([sys.executable, "-c", harness, str(HERE), label],
                                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
                         for label in ("global", "china")]
            for process in processes:
                out, err = process.communicate(timeout=15)
                self.assertEqual(process.returncode, 0, err)
                self.assertNotIn("synthetic-", out + err)
            self.assertEqual({path: path.read_bytes() for path in files}, before)

    def test_parallel_same_origin_updates_keep_other_site_intact(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            env = self.environment(root)
            self.configure(HERE, env, CN, "synthetic-china-key")
            china = root / "config/databend-cloud/credentials/api.databend.cn.json"
            before = china.read_bytes()
            processes = [subprocess.Popen([sys.executable, str(HERE / "cloud_config.py"), "set-key", "--stdin", "--base-url", COM],
                                         stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
                         for _ in range(4)]
            for index, process in enumerate(processes):
                process.stdin.write(f"synthetic-update-{index}")
                process.stdin.close()
                process.stdin = None
            for process in processes:
                out, err = process.communicate(timeout=15)
                self.assertEqual(process.returncode, 0, err)
                self.assertNotIn("synthetic-", out + err)
            self.assertEqual(china.read_bytes(), before)
            saved = json.loads(china.with_name("api.databend.com.json").read_text())
            self.assertIn(saved["api_key"], {f"synthetic-update-{index}" for index in range(4)})
            self.assertEqual(list(china.parent.glob("*.lock")), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
