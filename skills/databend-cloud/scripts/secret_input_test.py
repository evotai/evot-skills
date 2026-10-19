#!/usr/bin/env python3
"""Synthetic-key unit tests and real POSIX pseudo-terminal CLI tests; no network."""
import json
import os
from pathlib import Path
import select
import subprocess
import sys
import tempfile
import time
import unittest

import secret_input

TOKEN = "fake-preview-token-for-terminal-tests-1234"
SCRIPT = Path(__file__).resolve().with_name("cloud_config.py")


class EditorTest(unittest.TestCase):
    def edit(self, events):
        iterator = iter(events)
        sizes = []
        result = secret_input.edit_line(lambda: next(iterator), sizes.append)
        return result, sizes

    def test_masked_preview_has_only_prefix_and_suffix(self):
        preview = secret_input.masked_preview(TOKEN)
        self.assertTrue(preview.startswith(TOKEN[:4]))
        self.assertTrue(preview.endswith(TOKEN[-4:]))
        self.assertNotIn(TOKEN[4:-4], preview)
        self.assertIn("*", preview)

    def test_short_keys_are_fully_masked(self):
        for size in range(1, 16):
            self.assertEqual(secret_input.masked_preview("x" * size), "*" * size)

    def test_typing_sends_only_lengths_to_live_renderer(self):
        value, rendered = self.edit(list(TOKEN) + ["\r"])
        self.assertEqual(value, TOKEN)
        self.assertEqual(rendered, list(range(len(TOKEN) + 1)))

    def test_blank_and_spaces_are_invalid(self):
        for events in (["\r"], list("   ") + ["\r"]):
            with self.assertRaises(secret_input.InputError):
                self.edit(events)

    def test_backspace_and_clear(self):
        self.assertEqual(self.edit(list(TOKEN + "x") + ["\x7f", "\r"])[0], TOKEN)
        self.assertEqual(self.edit(list("wrong") + ["\x15"] + list(TOKEN) + ["\r"])[0], TOKEN)

    def test_bracketed_paste_trailing_newline_does_not_submit(self):
        events = ["PASTE_START"] + list(TOKEN + "\r\n") + ["PASTE_END", "\r"]
        self.assertEqual(self.edit(events)[0], TOKEN)

    def test_embedded_multiline_paste_rejected(self):
        events = ["PASTE_START"] + list(TOKEN + "\nsecond") + ["PASTE_END", "\r"]
        with self.assertRaises(secret_input.InputError):
            self.edit(events)

    def test_cancel_and_eof(self):
        for event, error in (("\x03", KeyboardInterrupt), ("\x04", EOFError), ("", EOFError)):
            with self.assertRaises(error):
                self.edit(list(TOKEN) + [event])

    def test_controls_are_data_not_actions_during_paste(self):
        events = ["PASTE_START"] + list(TOKEN + "\x03") + ["PASTE_END", "\r"]
        with self.assertRaises(secret_input.InputError):
            self.edit(events)

    def test_oversized_input_is_not_silently_truncated(self):
        with self.assertRaises(secret_input.InputError):
            self.edit(["x"] * (secret_input.MAX_KEY_LENGTH + 20) + ["\r"])

    def test_clear_recovers_from_oversized_input(self):
        events = ["x"] * (secret_input.MAX_KEY_LENGTH + 20) + ["\x15"] + list(TOKEN) + ["\r"]
        self.assertEqual(self.edit(events)[0], TOKEN)

    def test_control_and_unicode_never_reach_preview(self):
        for token in ("abc\x1bdef", "abc\x00def", "abc\x7fdef", "abc\tdef", "abc中def"):
            with self.assertRaises(secret_input.InputError):
                secret_input.validate_key(token)


@unittest.skipUnless(os.name == "posix", "Real terminal tests require POSIX pty")
class TerminalTest(unittest.TestCase):
    def setUp(self):
        import pty
        import termios

        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.master, self.slave = pty.openpty()
        self.addCleanup(os.close, self.master)
        self.addCleanup(os.close, self.slave)
        self.original = termios.tcgetattr(self.slave)
        self.environment = {key: value for key, value in os.environ.items() if key in ("PATH", "SYSTEMROOT", "WINDIR")}
        self.environment.update({"HOME": self.temporary.name, "XDG_CONFIG_HOME": self.temporary.name})
        self.path = Path(self.temporary.name) / "databend-cloud/credentials/api.databend.com.json"
        self.output = b""
        self.process = None
        self.addCleanup(self.stop)

    def stop(self):
        if self.process and self.process.poll() is None:
            self.process.kill()
            self.process.wait(timeout=5)

    def start(self, *extra):
        self.process = subprocess.Popen([sys.executable, str(SCRIPT), "set-key", "--base-url", "https://api.databend.com", *extra],
                                        stdin=self.slave, stdout=self.slave, stderr=self.slave, env=self.environment)
        self.until(secret_input.PROMPT.encode())

    def until(self, text):
        deadline = time.monotonic() + 5
        while text not in self.output:
            if time.monotonic() >= deadline:
                self.fail(f"Terminal did not show expected text {text!r}; exit={self.process.poll()}")
            if select.select([self.master], [], [], 0.05)[0]:
                self.output += os.read(self.master, 65536)

    def send(self, text):
        os.write(self.master, text if isinstance(text, bytes) else text.encode())

    def finish(self, expected=0):
        import termios

        deadline = time.monotonic() + 5
        # Drain while waiting: a PTY is flow-controlled, including tcsetattr's drain.
        while True:
            ready = select.select([self.master], [], [], 0.05)[0]
            if ready:
                self.output += os.read(self.master, 65536)
            elif self.process.poll() is not None:
                break
            if time.monotonic() >= deadline:
                self.fail("Terminal process did not exit after submission or cancellation")
        self.assertEqual(self.process.wait(timeout=1), expected)
        self.assertEqual(termios.tcgetattr(self.slave), self.original)
        self.assertNotIn(TOKEN.encode(), self.output)
        self.assertNotIn(TOKEN[4:-4].encode(), self.output)

    def test_paste_has_live_feedback_and_one_final_masked_preview(self):
        self.start()
        self.send(TOKEN)
        self.until(f"({len(TOKEN)} characters)".encode())
        self.assertIn(b"********", self.output)
        self.assertNotIn(TOKEN[:4].encode(), self.output)
        self.assertFalse(self.path.exists())
        self.send("\r")
        self.finish()
        preview = secret_input.masked_preview(TOKEN).encode()
        self.assertEqual(self.output.count(preview), 1)
        self.assertIn(b"Credential saved privately", self.output)
        self.assertEqual(json.loads(self.path.read_text())["api_key"], TOKEN)

    def test_empty_enter_retries_without_saving(self):
        self.start()
        self.send("\r")
        self.until(b"API key cannot be empty")
        self.assertFalse(self.path.exists())
        self.assertIsNone(self.process.poll())
        self.send(TOKEN + "\r")
        self.finish()
        self.assertEqual(json.loads(self.path.read_text())["api_key"], TOKEN)

    def test_cancel_never_creates_credentials(self):
        self.start()
        self.send(TOKEN + "\x03")
        self.finish(expected=2)
        self.assertFalse(self.path.exists())
        self.assertNotIn(b"Credential saved", self.output)

    def test_eof_never_creates_credentials(self):
        self.start()
        self.send("\x04")
        self.finish(expected=2)
        self.assertFalse(self.path.exists())

    def test_paste_with_trailing_newline_waits_for_enter(self):
        self.start()
        self.send("\x1b[200~" + TOKEN + "\r\n\x1b[201~")
        self.until(f"({len(TOKEN) + 2} characters)".encode())
        self.assertFalse(self.path.exists())
        self.assertIsNone(self.process.poll())
        self.send("\r")
        self.finish()
        self.assertEqual(json.loads(self.path.read_text())["api_key"], TOKEN)

    def test_multiline_paste_is_rejected(self):
        self.start()
        self.send("\x1b[200~" + TOKEN + "\nsecond\x1b[201~\r")
        self.until(b"without spaces or line breaks")
        self.assertFalse(self.path.exists())
        self.send("\x04")
        self.finish(expected=2)

    def test_editing_before_submit_saves_only_corrected_value(self):
        self.start()
        self.send("wrong\x15" + TOKEN + "x\x7f\r")
        self.finish()
        self.assertEqual(json.loads(self.path.read_text())["api_key"], TOKEN)

    def test_short_key_never_displays_any_of_its_characters(self):
        self.start()
        self.send("xyz\r")
        self.finish()
        self.assertIn(b"API key received: *** (3 characters)", self.output)
        self.assertNotIn(b"xyz", self.output)

    def test_reentering_key_replaces_same_site_without_extra_flag(self):
        self.path.parent.mkdir(parents=True)
        self.path.write_text(json.dumps({"base_url": "https://api.databend.com", "api_key": "previous-synthetic-value"}))
        self.path.chmod(0o600)
        self.start()
        self.send(TOKEN + "\r")
        self.finish()
        self.assertEqual(json.loads(self.path.read_text())["api_key"], TOKEN)

    def test_empty_rotation_and_cancel_preserve_existing_file(self):
        self.path.parent.mkdir(parents=True)
        original = json.dumps({"base_url": "https://api.databend.com", "api_key": "previous-synthetic-value"})
        self.path.write_text(original)
        self.path.chmod(0o600)
        self.start()
        self.send("\r")
        self.until(b"API key cannot be empty")
        self.assertEqual(self.path.read_text(), original)
        self.send("\x03")
        self.finish(expected=2)
        self.assertEqual(self.path.read_text(), original)


if __name__ == "__main__":
    unittest.main(verbosity=2)
