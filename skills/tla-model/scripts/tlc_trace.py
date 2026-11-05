#!/usr/bin/env python3
"""Summarize a TLC counterexample: each step's action and only the fields that changed."""
import argparse
import re
import sys
from pathlib import Path

HEADER = re.compile(r"^State (\d+): (.*)$")
ASSIGNMENT = re.compile(r"^(?:/\\ )?(\w+) = (.*)$")
TOKEN = re.compile(
    r'\s*(?:(?P<str>"(?:[^"\\]|\\.)*")|(?P<num>-?\d+)'
    r"|(?P<punct><<|>>|\|->|:>|@@|[\[\]{}(),])|(?P<id>[A-Za-z_][\w!.]*))"
)


class Record(dict):
    """[field |-> value, ...]"""


class Function(dict):
    """(key :> value @@ ...)"""


class Set(tuple):
    """{a, b}"""


class Seq(tuple):
    """<<a, b>>"""


def tokenize(text):
    tokens, pos = [], 0
    while pos < len(text):
        match = TOKEN.match(text, pos)
        if not match:
            if text[pos:].strip():
                raise ValueError(f"cannot tokenize near {text[pos:pos + 20]!r}")
            break
        tokens.append(match.group(match.lastgroup))
        pos = match.end()
    return tokens


def parse_value(text):
    tokens = tokenize(text)
    value, pos = _value(tokens, 0)
    if pos != len(tokens):
        raise ValueError("trailing tokens")
    return value


def _items(tokens, pos, close, kind):
    items = []
    while tokens[pos] != close:
        item, pos = _value(tokens, pos)
        items.append(item)
        if tokens[pos] == ",":
            pos += 1
    return kind(items), pos + 1


def _value(tokens, pos):
    token = tokens[pos]
    if token == "{":
        return _items(tokens, pos + 1, "}", Set)
    if token == "<<":
        return _items(tokens, pos + 1, ">>", Seq)
    if token == "[":
        record, pos = Record(), pos + 1
        while tokens[pos] != "]":
            if tokens[pos + 1] != "|->":
                raise ValueError("expected |->")
            record[tokens[pos]], pos = _value(tokens, pos + 2)
            if tokens[pos] == ",":
                pos += 1
        return record, pos + 1
    if token == "(":
        function, pos = Function(), pos + 1
        while tokens[pos] != ")":
            key, pos = _value(tokens, pos)
            if tokens[pos] != ":>":
                raise ValueError("expected :>")
            function[render(key)], pos = _value(tokens, pos + 1)
            if tokens[pos] == "@@":
                pos += 1
        return function, pos + 1
    if token in {"}", ">>", "]", ")", ",", "|->", ":>", "@@"}:
        raise ValueError(f"unexpected {token}")
    return token, pos + 1


def value_of(raw):
    try:
        return parse_value(raw)
    except (ValueError, IndexError):
        return " ".join(raw.split())


def render(value):
    if isinstance(value, Record):
        return "[" + ", ".join(f"{k} |-> {render(v)}" for k, v in value.items()) + "]"
    if isinstance(value, Function):
        return "(" + " @@ ".join(f"{k} :> {render(v)}" for k, v in value.items()) + ")"
    if isinstance(value, Set):
        return "{" + ", ".join(sorted(render(v) for v in value)) + "}"
    if isinstance(value, Seq):
        return "<<" + ", ".join(render(v) for v in value) + ">>"
    return str(value)


def diff(path, old, new, changes):
    if type(old) is type(new) and isinstance(new, dict):
        for key in list(old) + [k for k in new if k not in old]:
            child = f"{path}.{key}" if isinstance(new, Record) else f"{path}[{key}]"
            if key not in new or key not in old:
                before = render(old[key]) if key in old else "<absent>"
                after = render(new[key]) if key in new else "<absent>"
                changes.append((child, before, after))
            else:
                diff(child, old[key], new[key], changes)
    elif old is None or render(old) != render(new):
        changes.append((path, "<absent>" if old is None else render(old), render(new)))


def action_name(label):
    match = re.match(r"<(\w+) line \d+", label)
    return match.group(1) if match else label.strip("<>")


def parse_trace(text):
    """Return [(index, action, {variable: raw text})] for the first error trace."""
    states, current, variable = [], None, None
    for line in text.splitlines():
        header = HEADER.match(line)
        if header:
            if states and int(header.group(1)) == 1:
                break
            current, variable = {}, None
            states.append((int(header.group(1)), action_name(header.group(2)), current))
            continue
        if current is None:
            continue
        if not line.strip():
            current = None
            continue
        assignment = ASSIGNMENT.match(line)
        if assignment and (line.startswith("/\\ ") or not current):
            variable = assignment.group(1)
            current[variable] = assignment.group(2)
        elif variable:
            current[variable] += "\n" + line
    return states


def summarize(text, wanted=None, final=False):
    lines = [line for line in text.splitlines()
             if line.startswith("Error:") and "behavior up to this point" not in line]
    states = parse_trace(text)
    if not states:
        return lines + ["No counterexample trace found."]
    previous = None
    for index, action, raw in states:
        values = {k: value_of(v) for k, v in raw.items() if not wanted or k in wanted}
        lines.append(f"{index:>3} {action}")
        if previous is None:
            lines.extend(f"      {k} = {render(v)}" for k, v in values.items())
        else:
            changes = []
            for key, value in values.items():
                diff(key, previous.get(key), value, changes)
            lines.extend(f"      {p}: {old} -> {new}" for p, old, new in changes)
            if not changes:
                lines.append("      (no change in shown variables)" if wanted else "      (no change)")
        previous = values
    if final:
        lines.append("final state:")
        lines.extend(f"      {k} = {render(v)}" for k, v in previous.items())
    return lines


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", type=Path, help="tlc.log written by tlc_run.py or TLC")
    parser.add_argument("--vars", help="Comma-separated top-level variables to show")
    parser.add_argument("--final", action="store_true", help="Also print the full final state")
    args = parser.parse_args(argv)
    wanted = {v.strip() for v in args.vars.split(",") if v.strip()} if args.vars else None
    lines = summarize(args.log.read_text(errors="replace"), wanted, args.final)
    print("\n".join(lines))
    return 1 if lines and lines[-1] == "No counterexample trace found." else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except OSError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(1)
