#!/usr/bin/env python3
"""The runner here is a copy of the databend-cloud one; fail if the copies drift.

Both units must be independently installable, so each ships its own runner and
references cannot cross unit boundaries. That makes silent divergence the real
risk: a fix landing in one copy and not the other. This test catches it whenever
both units are present (the catalog, CI) and skips when only this unit is
installed.
"""
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
MINE = os.path.join(HERE, "query.py")
SIBLING = os.path.normpath(os.path.join(HERE, "..", "..", "databend-cloud", "scripts", "query.py"))


class RunnerParityTest(unittest.TestCase):
    def test_runner_matches_the_databend_cloud_unit(self):
        if not os.path.isfile(SIBLING):
            self.skipTest("databend-cloud unit not present; nothing to compare against")
        with open(MINE, "rb") as mine, open(SIBLING, "rb") as sibling:
            self.assertEqual(
                mine.read(),
                sibling.read(),
                "scripts/query.py has drifted from skills/databend-cloud/scripts/query.py; "
                "apply the change to both copies",
            )


if __name__ == "__main__":
    unittest.main()
