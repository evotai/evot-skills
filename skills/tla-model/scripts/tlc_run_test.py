#!/usr/bin/env python3
"""Offline tlc_run tests: archived jar identity and runner logic; no Java or network."""
import contextlib
import io
import json
import shutil
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import tlc_run

SUCCESS = (
    "Model checking completed. No error has been found.\n"
    "10 states generated, 8 distinct states found, 0 states left on queue.\n"
)
TRACE = (
    "Error: Invariant Safe is violated.\n"
    "Error: The behavior up to this point is:\nState 1: <Initial predicate>\n"
)
SPEC = {
    "module": "Model",
    "constants": {"N": 1, "Flag": True, "Mode": "fast"},
    "invariants": ["Safe"],
    "matrix": {"N": [1, 2], "Mode": ["fast", "slow"]},
    "cases": {
        "no_flag": {"constants": {"Flag": False}, "violation": "Safe"},
        "reachable": {"witness": "NeverDone"},
    },
    "scope": ["documentation keys are ignored"],
}


class VerdictTests(unittest.TestCase):
    def test_verdict(self):
        for code, text, expected, ok in [
            (0, SUCCESS, None, True),
            (0, "Starting...", None, False),
            (0, SUCCESS.replace("0 states left", "10 states left"), None, False),
            (-9, SUCCESS, None, False),
            (12, TRACE, "Safe", True),
            (0, TRACE, "Safe", False),
            (1, TRACE, "Safe", False),
            (12, TRACE, "Other", False),
            (12, TRACE, None, False),
            (12, TRACE.replace("State 1:", "No trace:"), "Safe", False),
            (12, TRACE + "Error: Unexpected exception\n", "Safe", False),
        ]:
            with self.subTest(code=code, text=text, expected=expected):
                self.assertEqual(tlc_run.verdict(code, text, expected), ok)


class CaseTests(unittest.TestCase):
    def test_matrix_mutation_and_witness(self):
        generated = tlc_run.cases(SPEC)
        self.assertEqual(len(generated), 6)
        self.assertIn("N=2,Mode=slow", generated)
        constants, invariants, expected = generated["reachable"]
        self.assertEqual((invariants, expected), (["Safe", "NeverDone"], "NeverDone"))
        self.assertEqual(generated["no_flag"][0]["Flag"], False)
        text = tlc_run.config_text(constants, invariants)
        for line in ['Flag = TRUE', 'Mode = "fast"', "INVARIANTS Safe NeverDone",
                     "CHECK_DEADLOCK FALSE"]:
            self.assertIn(line, text)

    def test_invalid_specs(self):
        bad = [
            {k: v for k, v in SPEC.items() if k != "module"},
            {**SPEC, "invariants": []},
            {**SPEC, "matrix": {"Unknown": [1]}},
            {**SPEC, "matrix": {"N": []}},
            {**SPEC, "matrix": {"Mode": ["a/b"]}},
            {**SPEC, "cases": {"bad name": {}}},
            {**SPEC, "cases": {"x": {"typo": 1}}},
            {**SPEC, "cases": {"x": {"constants": {"Unknown": 1}}}},
            {**SPEC, "cases": {"x": {"witness": "W", "invariants": []}}},
            {**SPEC, "cases": {"x": {"violation": "Other"}}},
        ]
        for spec in bad:
            with self.subTest(spec=spec), self.assertRaises(ValueError):
                tlc_run.cases(spec)
        for value in [1.5, None, 'quote"d', [1]]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                tlc_run.literal(value)


class JarTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.jar = self.root / "cache" / "tools.jar"
        network = mock.patch("urllib.request.urlopen", side_effect=AssertionError("network used"))
        self.urlopen = network.start()
        self.addCleanup(network.stop)
        output = contextlib.redirect_stdout(io.StringIO())
        output.__enter__()
        self.addCleanup(output.__exit__, None, None, None)

    def test_archive_identity_matches_manifest(self):
        tlc_run.verify_jar(tlc_run.ARCHIVED_JAR)
        self.assertEqual(tlc_run.ARCHIVED_JAR.parent.name, tlc_run.JAR_SHA256)
        self.assertEqual(tlc_run.DEFAULT_JAR.parent.name, tlc_run.JAR_SHA256)
        self.assertEqual(tlc_run.JAR_IDENTITY["schema_version"], 1)
        with zipfile.ZipFile(tlc_run.ARCHIVED_JAR) as jar:
            manifest = dict(line.split(": ", 1) for line in
                            jar.read("META-INF/MANIFEST.MF").decode().splitlines() if ": " in line)
        for field, attribute in [
            ("source_commit", "X-Git-Revision"),
            ("build_id", "X-Git-BuildNumber"),
            ("build_timestamp", "Build-TimeStamp"),
            ("implementation_version", "Implementation-Version"),
        ]:
            self.assertEqual(tlc_run.JAR_IDENTITY[field], manifest[attribute])
        self.assertEqual(tlc_run.JAR_IDENTITY["sha256"], tlc_run.JAR_SHA256)

    def test_missing_requires_explicit_install(self):
        with self.assertRaisesRegex(ValueError, "--install.*--download"):
            tlc_run.prepare_jar(self.jar, download=False)
        self.assertFalse(self.jar.parent.exists())
        self.urlopen.assert_not_called()

    def test_clean_install_is_offline_and_survives_cache_deletion(self):
        for _ in range(2):
            tlc_run.prepare_jar(self.jar, download=True)
            tlc_run.verify_jar(self.jar)
            self.assertEqual(list(self.jar.parent.iterdir()), [self.jar])
            self.jar.unlink()
        self.urlopen.assert_not_called()

    def test_existing_verified_cache_needs_neither_archive_nor_permission(self):
        tlc_run.prepare_jar(self.jar, download=True)
        with mock.patch.object(tlc_run, "ARCHIVED_JAR", self.root / "absent.jar"):
            tlc_run.prepare_jar(self.jar, download=False)

    def test_wrong_existing_jar_is_never_overwritten(self):
        self.jar.parent.mkdir()
        self.jar.write_bytes(b"different upstream build")
        for download in (False, True):
            with self.subTest(download=download), self.assertRaisesRegex(
                ValueError, "SHA-256 mismatch.*expected.*got"
            ):
                tlc_run.prepare_jar(self.jar, download=download)
            self.assertEqual(self.jar.read_bytes(), b"different upstream build")
        self.urlopen.assert_not_called()

    def test_missing_archive_has_no_network_fallback(self):
        with mock.patch.object(tlc_run, "ARCHIVED_JAR", self.root / "absent.jar"):
            with self.assertRaisesRegex(ValueError, "archive missing.*reinstall"):
                tlc_run.prepare_jar(self.jar, download=True)
        self.assertFalse(self.jar.exists())
        self.urlopen.assert_not_called()

    def test_corrupt_archive_is_rejected_before_install(self):
        archive = self.root / "wrong.jar"
        archive.write_bytes(b"not the pinned jar")
        with mock.patch.object(tlc_run, "ARCHIVED_JAR", archive):
            with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                tlc_run.prepare_jar(self.jar, download=True)
        self.assertFalse(self.jar.parent.exists())

    def test_corrupt_staged_copy_is_not_published(self):
        with mock.patch.object(tlc_run.shutil, "copyfileobj",
                               side_effect=lambda source, out: out.write(b"partial copy")):
            with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                tlc_run.prepare_jar(self.jar, download=True)
        self.assertEqual(list(self.jar.parent.iterdir()), [])

    def test_copy_sync_or_rename_failure_leaves_no_live_jar(self):
        for target in ("shutil.copyfileobj", "os.fsync", "Path.replace"):
            with self.subTest(target=target), mock.patch(
                f"tlc_run.{target}", side_effect=OSError("injected failure")
            ):
                with self.assertRaisesRegex(OSError, "injected failure"):
                    tlc_run.prepare_jar(self.jar, download=True)
                self.assertEqual(list(self.jar.parent.iterdir()), [])

    def test_verified_legacy_cache_migrates_without_permission(self):
        legacy = self.root / "tla2tools-1.8.0.jar"
        shutil.copyfile(tlc_run.ARCHIVED_JAR, legacy)
        with mock.patch.object(tlc_run, "DEFAULT_JAR", self.jar), \
                mock.patch.object(tlc_run, "LEGACY_JAR", legacy):
            tlc_run.prepare_jar(self.jar, download=False)
        tlc_run.verify_jar(self.jar)
        tlc_run.verify_jar(legacy)

    def test_wrong_legacy_cache_is_not_relabelled_or_silently_replaced(self):
        legacy = self.root / "tla2tools-1.8.0.jar"
        legacy.write_bytes(b"floating release replacement")
        with mock.patch.object(tlc_run, "DEFAULT_JAR", self.jar), \
                mock.patch.object(tlc_run, "LEGACY_JAR", legacy):
            with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                tlc_run.prepare_jar(self.jar, download=True)
        self.assertFalse(self.jar.exists())
        self.assertEqual(legacy.read_bytes(), b"floating release replacement")


class ExecutionTests(unittest.TestCase):
    def test_timeout_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            args = SimpleNamespace(java="unused", timeout=1, workers=1)
            with mock.patch("tlc_run.subprocess.run",
                            side_effect=subprocess.TimeoutExpired("tlc", 1)), \
                    contextlib.redirect_stdout(io.StringIO()):
                self.assertFalse(tlc_run.run_case(args, Path("x.jar"), Path(directory), "M", None))

    def test_install_aliases_and_run_identity(self):
        for flag in ("--install", "--download"):
            with self.subTest(flag=flag), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                model = root / "model"
                model.mkdir()
                (model / "model.json").write_text(json.dumps(SPEC))
                (model / "Model.tla").write_text("---- MODULE Model ----\n====\n")
                jar = root / "cache" / "tools.jar"
                output = root / "artifacts"
                with mock.patch("tlc_run.subprocess.run"), \
                        mock.patch("tlc_run.run_case", return_value=True), \
                        mock.patch("urllib.request.urlopen", side_effect=AssertionError("network used")), \
                        contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(tlc_run.main([
                        str(model), flag, "--jar", str(jar), "--output", str(output)
                    ]), 0)
                tlc_run.verify_jar(jar)
                self.assertEqual(json.loads((output / "toolchain.json").read_text()),
                                 tlc_run.JAR_IDENTITY)

    def test_list_needs_no_java(self):
        with tempfile.TemporaryDirectory() as directory:
            model = Path(directory)
            (model / "model.json").write_text(json.dumps(SPEC))
            out = io.StringIO()
            with mock.patch("tlc_run.subprocess.run") as run, contextlib.redirect_stdout(out):
                self.assertEqual(tlc_run.main([str(model), "--list"]), 0)
                run.assert_not_called()
            self.assertEqual(len(out.getvalue().split()), 6)


if __name__ == "__main__":
    unittest.main()
