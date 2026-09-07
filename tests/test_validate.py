"""Fast catalog display validation tests; no network or skill prerequisites."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location(
    'validate', Path(__file__).resolve().parents[1] / 'scripts' / 'validate.py')
validate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validate)


class DisplayTests(unittest.TestCase):
    def setUp(self):
        self.data = {
            'schema_version': 1,
            'summary': 'Work with Feishu messages, docs, and calendars',
            'example': "lark: What's new in my alerts group?",
        }

    def test_valid_and_additive_fields(self):
        self.assertEqual(validate.validate_display(self.data, 'lark'), [])
        self.assertEqual(validate.validate_display({**self.data, 'future_hint': True}, 'lark'), [])

    def test_versions_and_object_shape(self):
        for version in [None, 0, 2, True, '1']:
            with self.subTest(version=version):
                self.assertTrue(validate.validate_display({**self.data, 'schema_version': version}, 'lark'))
        for data in [None, [], 'text', {'summary': 'Missing version'}]:
            self.assertTrue(validate.validate_display(data, 'lark'))

    def test_text_and_prefix(self):
        for field, maximum in [('summary', 60), ('example', 96)]:
            for value in ['', ' padded ', 'line\nbreak', '\x1b[31mred', '中文', 'x' * (maximum + 1), 1]:
                with self.subTest(field=field, value=value):
                    self.assertTrue(validate.validate_display({**self.data, field: value}, 'lark'))
        for example in ['Show alerts', 'opencli: Show alerts', 'lark: ']:
            self.assertTrue(validate.validate_display({**self.data, 'example': example}, 'lark'))

    def test_file_errors_and_valid_file(self):
        with tempfile.TemporaryDirectory() as root:
            unit = Path(root) / 'lark'
            unit.mkdir()
            path = unit / '.display.json'
            for content in [None, '{', 'x' * 4097, json.dumps({'schema_version': 2})]:
                if content is not None:
                    path.write_text(content)
                errors = []
                validate.check_display(str(unit), errors)
                self.assertTrue(errors)
            path.write_text(json.dumps(self.data))
            errors = []
            validate.check_display(str(unit), errors)
            self.assertEqual(errors, [])

    def test_every_catalog_unit(self):
        for unit in validate.visible_dirs(validate.SKILLS):
            with self.subTest(unit=unit):
                errors = []
                validate.check_display(str(Path(validate.SKILLS) / unit), errors)
                self.assertEqual(errors, [])


if __name__ == '__main__':
    unittest.main()
