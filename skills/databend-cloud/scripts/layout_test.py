#!/usr/bin/env python3
"""Keep the single entrypoint short and all on-demand references self-contained."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
LINK = re.compile(r"\[[^\]]*\]\(([^)#\s]+)(?:#[^)]*)?\)")
SCRIPT = re.compile(r"(?:^|[\s`(])(scripts/[A-Za-z0-9._/-]+\.[A-Za-z0-9]+)")


class LayoutTest(unittest.TestCase):
    def setUp(self):
        self.main = (ROOT / "SKILL.md").read_text()

    def test_entrypoint_stays_short(self):
        self.assertLessEqual(len(self.main.splitlines()), 90, "Move task detail into references, not SKILL.md")

    def test_incident_detail_is_loaded_only_from_references(self):
        self.assertIn("references/troubleshooting/index.md", self.main)
        self.assertIn("Load only the references needed", self.main)
        for detail in ("peek_memory_usage", "session_settings", "log_type_name", "query_out_of_memory_behavior"):
            self.assertNotIn(detail, self.main)
        for name in ("index.md", "log-schema.md", "query-recipes.md", "memory.md", "log-export.md"):
            self.assertTrue((ROOT / "references/troubleshooting" / name).is_file())

    def test_base_dependency_does_not_require_jq(self):
        self.assertIn("bins: [python3]", self.main)
        frontmatter = self.main.split("---", 2)[1]
        self.assertNotRegex(frontmatter, r"bins:\s*\[[^\]]*\bjq\b")
        self.assertIn("jq is optional", self.main)

    def test_read_only_incident_boundary_is_at_entrypoint(self):
        self.assertIn("Incident investigation is read-only", self.main)
        self.assertIn("explicitly authorized task", self.main)
        workflow = (ROOT / "references/troubleshooting/index.md").read_text()
        self.assertIn("Never", workflow)
        self.assertIn("terminal", workflow)
        self.assertIn("read-only", workflow)

    def test_all_markdown_links_remain_inside_install_unit(self):
        for path in ROOT.rglob("*.md"):
            for target in LINK.findall(path.read_text()):
                if target.startswith(("https://", "http://", "mailto:", "/")):
                    continue
                with self.subTest(file=str(path.relative_to(ROOT)), target=target):
                    resolved = (path.parent / target).resolve()
                    self.assertTrue(resolved.is_relative_to(ROOT))
                    self.assertTrue(resolved.is_file(), "Broken reference after moving incident documents")

    def test_script_examples_resolve_from_skill_root(self):
        for path in ROOT.rglob("*.md"):
            for target in SCRIPT.findall(path.read_text()):
                with self.subTest(file=str(path.relative_to(ROOT)), target=target):
                    self.assertTrue((ROOT / target).is_file())

    def test_version_and_date_are_explicit(self):
        self.assertRegex(self.main, r'version: "\d+\.\d+\.\d+"')
        self.assertRegex(self.main, r'updated_at: "\d{4}-\d{2}-\d{2}"')
        self.assertTrue((ROOT / "CHANGELOG.md").is_file())

    def test_no_legacy_context_or_dsn_registry_in_guides(self):
        for path in [ROOT / "SKILL.md", *(ROOT / "references").rglob("*.md")]:
            for obsolete in ("--context", "set-context", "list-contexts", "--config-file", "DATABEND_CLOUD_CONTEXT",
                             "config.json", "BENDCLOUD_DSN"):
                with self.subTest(file=path.name, removed=obsolete):
                    self.assertNotIn(obsolete, path.read_text())

    def test_target_registry_is_resolved_before_asking(self):
        before = self.main.split("## Helpers")[0]
        self.assertIn("list-targets", before)
        self.assertIn("set-target", before)
        self.assertIn("no default or active target", self.main)
        organizations = (ROOT / "references/organizations.md").read_text()
        self.assertIn("targets.json", organizations)
        self.assertIn("list-targets", organizations)
        self.assertIn("remove-target", organizations)
        self.assertIn("list-targets", (ROOT / "references/troubleshooting/index.md").read_text())

    def test_one_runtime_and_no_parity_cruft(self):
        for name in ("cloud_config.py", "secret_input.py", "query.py", "query_api.py", "format_log_history.jq"):
            self.assertEqual(len(list(ROOT.rglob(name))), 1, name)
        self.assertFalse((ROOT / "scripts/runner_parity_test.py").exists())
        self.assertFalse((ROOT.parent / "databend-cloud-troubleshooting").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
