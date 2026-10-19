#!/usr/bin/env python3
"""Private terminal API-key input: live stars, then a single masked preview."""
from contextlib import contextmanager
import os
import sys

MAX_KEY_LENGTH = 16384
PROMPT = "Paste Databend Cloud API key; Enter saves, Ctrl+C cancels."


class InputError(ValueError):
    pass


def validate_key(value):
    if not isinstance(value, str) or not value:
        raise InputError("API key cannot be empty. Paste a key and press Enter.")
    if len(value) > MAX_KEY_LENGTH:
        raise InputError("API key is too long. Clear it and paste a single key.")
    if any(not 33 <= ord(character) <= 126 for character in value):
        raise InputError("API key must be a single printable token without spaces or line breaks.")
    return value


def masked_preview(value):
    """Never reveal a complete short key, or a changing suffix during typing."""
    if len(value) < 16:
        return "*" * len(value)
    return value[:4] + "*" * min(len(value) - 8, 24) + value[-4:]


def edit_line(event, render):
    """An event is one character, or a bracketed-paste/editing control name."""
    value, pasting, overflow = [], False, False
    render(0)
    while True:
        character = event()
        if character == "PASTE_START":
            pasting = True
            continue
        if character == "PASTE_END":
            pasting = False
            continue
        if character == "IGNORE":
            continue
        if character == "":
            raise EOFError
        if not pasting:
            if character == "\x03":
                raise KeyboardInterrupt
            if character == "\x04":
                raise EOFError
            if character in ("\r", "\n"):
                if overflow:
                    raise InputError("API key is too long. Clear it and paste a single key.")
                # A copied trailing newline is harmless; embedded lines remain invalid.
                return validate_key("".join(value).rstrip("\r\n"))
            if character in ("\x7f", "\b"):
                if value:
                    value.pop()
                render(len(value))
                continue
            if character == "\x15":  # Ctrl+U: clear input, including an overflowed paste.
                value, overflow = [], False
                render(0)
                continue
        if len(value) <= MAX_KEY_LENGTH:
            value.append(character)
        else:
            overflow = True
        render(len(value))


@contextmanager
def terminal_events():
    """Disable OS echo before the prompt. Never fall back to echoed input."""
    if not sys.stdin.isatty() or not sys.stderr.isatty():
        raise InputError("Use a private interactive terminal for masked input, or --stdin with a secret-manager pipe")
    if os.name == "posix":
        import select
        import termios
        import tty

        fd = sys.stdin.fileno()
        original = termios.tcgetattr(fd)

        def event():
            first = os.read(fd, 1).decode("latin1")
            if first != "\x1b":
                return first
            sequence = ""
            while len(sequence) < 16 and select.select([fd], [], [], 0.1)[0]:
                character = os.read(fd, 1).decode("latin1")
                if not character:
                    raise EOFError
                sequence += character
                if sequence == "[200~":
                    return "PASTE_START"
                if sequence == "[201~":
                    return "PASTE_END"
                if len(sequence) > 1 and (character.isalpha() or character == "~"):
                    break
            return "IGNORE"

        try:
            tty.setraw(fd, termios.TCSANOW)
            sys.stderr.write("\x1b[?2004h")
            sys.stderr.flush()
            yield event
        finally:
            try:
                sys.stderr.write("\x1b[?2004l")
                sys.stderr.flush()
            finally:
                # Discard leftover pasted input rather than handing it back to the shell.
                termios.tcsetattr(fd, termios.TCSAFLUSH, original)
    elif os.name == "nt":
        import msvcrt

        def event():
            character = msvcrt.getwch()
            if character in ("\x00", "\xe0"):
                msvcrt.getwch()  # Ignore arrows/function keys, never add them to a key.
                return "IGNORE"
            return character

        yield event
    else:
        raise InputError("Masked terminal input is unavailable here; use a private secret-manager pipe with --stdin")


def read_key():
    """Keep only stars in live redraws; show a prefix/suffix once after validation."""
    with terminal_events() as event:
        sys.stderr.write(PROMPT + "\r\n")
        sys.stderr.flush()

        def render(length):
            sys.stderr.write("\r\x1b[2KAPI key: " + "*" * min(length, 32)
                             + (f" ({length} characters)" if length else ""))
            sys.stderr.flush()

        try:
            while True:
                try:
                    value = edit_line(event, render)
                except InputError as error:
                    sys.stderr.write("\r\n" + str(error) + "\r\n")
                    sys.stderr.flush()
                    continue
                sys.stderr.write("\r\x1b[2KAPI key received: " + masked_preview(value)
                                 + f" ({len(value)} characters)\r\n")
                sys.stderr.flush()
                return value
        except (EOFError, KeyboardInterrupt):
            sys.stderr.write("\r\n")
            sys.stderr.flush()
            raise
