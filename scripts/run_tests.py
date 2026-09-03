#!/usr/bin/env python3
"""Discover and run every *_test.py that ships alongside a skill."""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS = os.path.join(ROOT, "skills")


def test_files():
    found = []
    for base, dirs, files in os.walk(SKILLS):
        dirs[:] = [name for name in dirs if not name.startswith(".")]
        for name in sorted(files):
            if name.endswith("_test.py"):
                found.append(os.path.join(base, name))
    return sorted(found)


def main():
    files = test_files()
    if not files:
        print("no test files found")
        return 0

    failed = []
    for path in files:
        rel = os.path.relpath(path, ROOT)
        directory, name = os.path.split(path)
        result = subprocess.run(
            [sys.executable, name],
            cwd=directory,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            summary = result.stderr.strip().splitlines()
            print(f"PASS  {rel}  {summary[-1] if summary else ''}")
        else:
            failed.append(rel)
            print(f"FAIL  {rel}", file=sys.stderr)
            print(result.stdout, file=sys.stderr)
            print(result.stderr, file=sys.stderr)

    if failed:
        print(f"\n{len(failed)} failing test file(s): {', '.join(failed)}", file=sys.stderr)
        return 1
    print(f"\nOK    {len(files)} test file(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
