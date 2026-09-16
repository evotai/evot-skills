#!/usr/bin/env python3
"""Contract test for the human-readable log_history formatter."""
import json
import os
import shutil
import subprocess
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "format_log_history.jq")
JQ = shutil.which("jq")

COLUMNS = [
    "timestamp",
    "path",
    "target",
    "log_level",
    "cluster_id",
    "node_id",
    "warehouse_id",
    "query_id",
    "message",
    "fields",
    "batch_number",
]


def schema_line():
    return json.dumps([{"name": name, "type": "Nullable(String)"} for name in COLUMNS])


def row(
    timestamp="2026-09-16 10:35:30.519941",
    path="p",
    target="t",
    level="WARN",
    cluster="c",
    node="n",
    warehouse="w",
    query="q",
    message="m",
    fields="f",
    batch=1,
):
    return json.dumps([timestamp, path, target, level, cluster, node, warehouse, query, message, fields, batch])


@unittest.skipUnless(JQ, "jq is required to exercise the formatter")
class FormatLogHistoryTest(unittest.TestCase):
    def format(self, *lines):
        result = subprocess.run(
            [JQ, "-r", "-f", SCRIPT],
            input="\n".join(lines) + "\n",
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def test_schema_line_is_dropped(self):
        self.assertEqual(self.format(schema_line(), row()).count("\n"), 1)

    def test_utc_timestamp_becomes_utc_plus_8_with_milliseconds(self):
        out = self.format(schema_line(), row(timestamp="2026-09-16 10:35:30.519941"))
        self.assertTrue(out.startswith("2026-09-16 18:35:30.519 WARN [0] WARN - q - m"), out)

    def test_control_characters_keep_one_event_per_line(self):
        out = self.format(schema_line(), row(message="line\nwith\ttab"))
        self.assertEqual(out.count("\n"), 1)
        self.assertIn(r"line\nwith\ttab", out)

    def test_event_without_a_timestamp_is_still_reported(self):
        out = self.format(schema_line(), row(timestamp=None))
        self.assertTrue(out.startswith("- WARN"), out)

    def test_missing_optional_fields_get_placeholders(self):
        out = self.format(schema_line(), row(level=None, query=None, fields=None))
        self.assertIn("INFO [0] INFO - - - m", out)
        self.assertTrue(out.endswith("fields=-\n"), out)

    def test_metadata_follows_the_message(self):
        out = self.format(
            schema_line(),
            row(path="pa", target="ta", cluster="cl", node="no", warehouse="wh", batch=7),
        )
        self.assertIn("| target=ta node_id=no warehouse_id=wh path=pa cluster_id=cl batch_number=7 fields=f", out)


if __name__ == "__main__":
    unittest.main()
