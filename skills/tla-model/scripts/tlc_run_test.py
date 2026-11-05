#!/usr/bin/env python3
"""Offline tlc_run tests: no Java, network or real jar."""
import contextlib
import io
import subprocess
import tempfile
import unittest
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


class ExecutionTests(unittest.TestCase):
    def test_timeout_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            args = SimpleNamespace(java="unused", timeout=1, workers=1)
            with mock.patch("tlc_run.subprocess.run",
                            side_effect=subprocess.TimeoutExpired("tlc", 1)), \
                    contextlib.redirect_stdout(io.StringIO()):
                self.assertFalse(tlc_run.run_case(args, Path("x.jar"), Path(directory), "M", None))

    def test_jar_checks_without_network(self):
        with tempfile.TemporaryDirectory() as directory:
            jar = Path(directory) / "tools.jar"
            with mock.patch("tlc_run.urllib.request.urlopen") as urlopen:
                with self.assertRaisesRegex(ValueError, "--download"):
                    tlc_run.prepare_jar(jar, download=False)
                urlopen.assert_not_called()
            jar.write_bytes(b"wrong toolchain")
            with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                tlc_run.prepare_jar(jar, download=False)

    def test_list_needs_no_java(self):
        with tempfile.TemporaryDirectory() as directory:
            model = Path(directory)
            (model / "model.json").write_text(__import__("json").dumps(SPEC))
            out = io.StringIO()
            with mock.patch("tlc_run.subprocess.run") as run, contextlib.redirect_stdout(out):
                self.assertEqual(tlc_run.main([str(model), "--list"]), 0)
                run.assert_not_called()
            self.assertEqual(len(out.getvalue().split()), 6)


if __name__ == "__main__":
    unittest.main()
