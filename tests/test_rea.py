"""Offline contracts for the official REA skill's CLI-only adaptation."""
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
UNIT = ROOT / 'skills' / 'rea'
GUIDES = {
    'connection-and-recovery', 'native-and-artifacts', 'javascript-applications',
    'android-applications', 'runtime-observation', 'evidence-workflows',
}
SPEC = importlib.util.spec_from_file_location('catalog_validate', ROOT / 'scripts' / 'validate.py')
validate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validate)


def text(name='SKILL.md'):
    return (UNIT / name).read_text()


def shell_blocks(markdown):
    return re.findall(r'```(?:bash|sh)\n(.*?)```', markdown, re.S)


class ReaSkillTests(unittest.TestCase):
    def test_frontmatter_install_identity_and_display(self):
        errors = []
        validate.check_display(str(UNIT), errors)
        self.assertEqual(errors, [])
        self.assertEqual(list(UNIT.rglob('SKILL.md')), [UNIT / 'SKILL.md'])
        block = validate.frontmatter(text())
        self.assertEqual(validate.top_level(block, 'name'), 'rea')
        self.assertEqual(validate.top_level(block, 'license'), 'MIT')
        self.assertIn('ordinary source-repository', validate.top_level(block, 'description'))
        self.assertIn('CLI-only', validate.top_level(block, 'compatibility'))
        self.assertIn('bins: [node]', '\n'.join(block))
        self.assertNotRegex('\n'.join(block), r'(?m)^\s*env:')

    def test_concise_entry_and_official_progressive_guides(self):
        self.assertLessEqual(len((UNIT / 'SKILL.md').read_bytes()), 4200)
        self.assertLessEqual(len(text().splitlines()), 60)
        self.assertEqual({p.stem for p in (UNIT / 'references').glob('*.md')}, GUIDES)
        for guide in GUIDES:
            self.assertIn(f'references/{guide}.md', text())
        self.assertIn('only the relevant guide', text())
        self.assertNotIn('rea providers --json', text())  # readiness is not a default ritual
        self.assertIn('summary-first', text())

    def test_local_links_and_heading_anchors(self):
        for path in UNIT.rglob('*.md'):
            for target in set(validate.LINK_RE.findall(path.read_text())):
                if target.startswith(('https://', 'http://')):
                    continue
                name, _, anchor = target.partition('#')
                resolved = (path.parent / name).resolve() if name else path.resolve()
                with self.subTest(file=path.name, target=target):
                    self.assertTrue(resolved.is_relative_to(UNIT.resolve()))
                    self.assertTrue(resolved.is_file())
                    if anchor:
                        headings = re.findall(r'^#{1,6}\s+(.+)$', resolved.read_text(), re.M)
                        slugs = {re.sub(r'[^\w\s-]', '', h.lower()).replace(' ', '-') for h in headings}
                        self.assertIn(anchor, slugs)

    def test_official_provenance_license_and_all_adapted_paths(self):
        manifest = json.loads(text('upstream.json'))
        self.assertEqual(manifest['repository'], 'https://github.com/morluto/rea')
        self.assertEqual(manifest['commit'], '60accad2de8f2862fe91901502fe26cc5390fb36')
        self.assertEqual(manifest['profile'], 'cli-only')
        self.assertEqual(manifest['license'], 'MIT')
        expected = {'LICENSE', 'SKILL.md'} | {f'references/{g}.md' for g in GUIDES}
        self.assertEqual({r['local_path'] for r in manifest['files']}, expected)
        for row in manifest['files']:
            with self.subTest(source=row['path']):
                self.assertRegex(row['sha256'], r'^[a-f0-9]{64}$')
                self.assertTrue((UNIT / row['local_path']).is_file())
                if row['mode'] == 'verbatim':
                    self.assertEqual(hashlib.sha256((UNIT / row['local_path']).read_bytes()).hexdigest(), row['sha256'])
                else:
                    self.assertEqual(row['mode'], 'adapted-selection')
                    self.assertIn('.agents/skills/reverse-engineer-anything/', row['path'])
        self.assertIn('Copyright (c) 2026 morluto', text('LICENSE'))
        self.assertIn('adapted selections', text('UPSTREAM.md'))
        self.assertIn(manifest['commit'], text('UPSTREAM.md'))

    def test_no_legacy_or_mcp_session_instructions(self):
        legacy = ('rea-cli', 'tool-routing', 'native-and-containers',
                  'runtime-and-evidence', 'source-reconstruction')
        for name in legacy:
            self.assertFalse((UNIT / 'references' / f'{name}.md').exists())
        for path in UNIT.rglob('*.md'):
            body = path.read_text()
            with self.subTest(file=path.name):
                for stale in ('mcp_servers.', 'tools/list', 'structuredContent',
                              '`open_binary`', '`close_binary`', '`binary_session`'):
                    self.assertNotIn(stale, body)
                for block in shell_blocks(body):
                    self.assertNotIn('--mcp', block)
                    self.assertNotRegex(block, r'(?m)^\s*rea (?:setup|environment-serve)\b')
        self.assertIn('not enabled', text('references/android-applications.md'))
        self.assertIn('MCP JAR', text('references/android-applications.md'))
        self.assertIn('No MCP registration', text())

    def test_no_direct_tool_or_custom_parser_fallback(self):
        forbidden = re.compile(
            r'(?m)(?:^|[;|&])\s*(?:\S*/)?'
            r'(?:objdump|llvm-objdump|strings|nm|readelf|otool|jadx|'
            r'analyzeHeadless|ghidra|hopper|ida|sqlite3|tshark)\b'
        )
        for path in UNIT.rglob('*.md'):
            for block in shell_blocks(path.read_text()):
                with self.subTest(file=path.name):
                    self.assertNotRegex(block, forbidden)
                    self.assertNotRegex(block, r'\b(?:import|from)\s+(?:capstone|elftools)\b')
        self.assertIn('substitute binary parsers', text())
        self.assertIn('even wrapped in `capture-process`', text())
        self.assertIn('do not bypass REA', text())

    def test_portable_cli_evidence_instead_of_cross_process_ids(self):
        evidence = text('references/evidence-workflows.md')
        self.assertIn('Each CLI invocation is a separate process', evidence)
        self.assertIn('cannot assume an in-memory retained Evidence ID', evidence)
        self.assertIn('authenticated bundle', evidence)
        template = re.search(r'```text\n(.*?)\n```', evidence, re.S).group(1)
        sample = {'evidence_id': 'synthetic-test-record', 'normalized_result': {}}
        request = json.loads(template.replace('COMPLETE_EVIDENCE_OBJECT', json.dumps(sample)))
        self.assertEqual(request['source'], {'kind': 'inline', 'evidence': sample})
        self.assertEqual(request['view'], {'kind': 'summary'})
        self.assertIn('rea inspect-analysis-view', evidence)

    def test_runner_recovery_pinned_acquisition_and_deadlines(self):
        recovery = text('references/connection-and-recovery.md')
        for required in ('rea --version', 'rea --help', 'rea providers --json',
                         'rea capabilities --json', 'provider_timeout', 'do not silently retry online'):
            self.assertIn(required, recovery)
        self.assertIn('acquisition is authorized', recovery)
        versions = re.findall(r'rea-agents@([^\s`]+)', recovery)
        self.assertEqual(versions, ['6.7.0'])
        self.assertIn('host command deadline', recovery)
        self.assertIn('No direct-tool fallback', recovery)

    def test_automatic_configuration_stays_scoped_and_requires_install_approval(self):
        recovery = text('references/connection-and-recovery.md')
        self.assertIn('Automatically diagnose and configure existing installations', text())
        for required in ('Existing installations, no persistent changes',
                         '/usr/libexec/java_home -V', 'GHIDRA_INSTALL_DIR', 'JAVA_HOME',
                         'current REA process/task', 'Shell variables do not persist',
                         'Do not edit shell profiles', 'multiple incompatible/ambiguous',
                         'ask for approval before downloads', 'Once approved, perform that setup',
                         'back up affected configuration', 'verify available vendor checksums',
                         'Do not pipe remote scripts', 'neither automatic repair nor installation approval'):
            self.assertIn(required, recovery)
        self.assertNotIn('REA CLI or REA MCP', text())

    def test_setup_success_requires_real_backend_verification(self):
        recovery = text('references/connection-and-recovery.md')
        for required in ('bounded read-only REA operation', 'using the selected engine',
                         'successful command status and an error-free result envelope',
                         'JS capture does not prove native analysis works',
                         'Avoid masking a failed command', 'actual exit status, full JSON, stderr',
                         'Resume the interrupted analysis only after that check succeeds',
                         'do not call setup successful'):
            self.assertIn(required, recovery)

    def test_source_request_delivers_code_tests_and_evidence(self):
        evidence = text('references/evidence-workflows.md')
        for required in ('actual reconstructed files', 'important code inline',
                         'not original vendor source', 'compile and run focused tests',
                         'supporting REA Evidence/addresses', 'uncompiled/untested'):
            self.assertIn(required, evidence)
        self.assertIn('static analysis is not observed execution', text())
        self.assertIn('expected backend/layout', evidence)
        self.assertIn('actual operator/backend', text())

    def test_bounded_capture_template_no_secrets(self):
        runtime = text('references/runtime-observation.md')
        self.assertIn('../assets/process-scenario.json', runtime)
        self.assertIn('command arguments, not scenario contents', runtime)
        self.assertIn('optimized-away cases', runtime)
        self.assertIn('zero wrapper exit', runtime)
        scenario = json.loads(text('assets/process-scenario.json'))
        self.assertTrue(Path(scenario['executable']).is_absolute())
        self.assertIn('/absolute/path/', scenario['executable'])
        self.assertTrue(Path(scenario['working_directory']).is_absolute())
        self.assertEqual(scenario['arguments'], [])
        self.assertEqual(scenario['environment'], {})
        self.assertEqual(scenario['filesystem_observation_paths'], [])
        self.assertGreater(scenario['idle_timeout_ms'], 0)
        self.assertLessEqual(scenario['idle_timeout_ms'], scenario['timeout_ms'])
        self.assertLessEqual(scenario['timeout_ms'], 60000)
        self.assertGreaterEqual(scenario['settle_ms'], 0)
        self.assertLessEqual(scenario['settle_ms'], scenario['idle_timeout_ms'])
        self.assertGreater(scenario['limits']['output_bytes'], 0)
        self.assertLessEqual(scenario['limits']['output_bytes'], 8000000)
        self.assertEqual(scenario['terminal']['scrollback'], 0)
        self.assertEqual(scenario['normalization'], {'paths': False, 'pids': False, 'ports': False})

    def test_javascript_coverage_and_runtime_identity_limits(self):
        javascript = text('references/javascript-applications.md')
        self.assertIn('analyze-javascript-application', javascript)
        self.assertIn('path can represent', javascript)
        self.assertIn('Module ordinals/minified names are not persistent identity', javascript)
        self.assertIn('not absence from the application', javascript)
        self.assertIn('No native engine', javascript)
        self.assertIn('Passive observation does not click', text('references/runtime-observation.md'))


if __name__ == '__main__':
    unittest.main()
