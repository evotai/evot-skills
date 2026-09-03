#!/usr/bin/env python3
"""Validate the skill catalog layout, frontmatter, and internal references."""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS = os.path.join(ROOT, "skills")
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)#\s]+)")
SCRIPT_RE = re.compile(
    r"(?:^|[\s`(])((?:scripts|references|assets)/[A-Za-z0-9._/-]+\.[A-Za-z0-9]+)"
)
MAX_LINES = 500
MAX_BYTES = 1_000_000


def visible_dirs(path):
    if not os.path.isdir(path):
        return []
    return sorted(
        name
        for name in os.listdir(path)
        if not name.startswith(".") and os.path.isdir(os.path.join(path, name))
    )


def frontmatter(text):
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return None
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            return lines[1:index]
    return None


def top_level(block, key):
    prefix = key + ":"
    for line in block:
        if line.startswith(prefix):
            value = line[len(prefix) :].strip()
            if len(value) > 1 and value[0] == value[-1] and value[0] in "\"'":
                return value[1:-1]
            return value
    return None


def check_skill(rel, errors, warnings):
    path = os.path.join(ROOT, rel)
    text = open(os.path.join(path, "SKILL.md"), encoding="utf-8").read()
    name = os.path.basename(rel)

    block = frontmatter(text)
    if block is None:
        errors.append(f"{rel}/SKILL.md: missing YAML frontmatter")
        return

    declared = top_level(block, "name")
    if declared != name:
        errors.append(f"{rel}/SKILL.md: name '{declared}' must equal directory name '{name}'")
    if not NAME_RE.match(name) or len(name) > 64:
        errors.append(f"{rel}: invalid skill name '{name}'")

    description = top_level(block, "description")
    if not description:
        errors.append(f"{rel}/SKILL.md: description is required")
    elif len(description) > 1024:
        errors.append(f"{rel}/SKILL.md: description exceeds 1024 characters")

    body_lines = text.count("\n") + 1
    if body_lines > MAX_LINES:
        warnings.append(f"{rel}/SKILL.md: {body_lines} lines (recommended max {MAX_LINES})")

    unit = rel.split(os.sep)[1]
    unit_dir = os.path.join(SKILLS, unit)
    targets = set(LINK_RE.findall(text)) | set(SCRIPT_RE.findall(text))
    for target in sorted(targets):
        if target.startswith(("http://", "https://", "mailto:", "/")):
            continue
        if "*" in target or "?" in target:
            continue
        resolved = os.path.normpath(os.path.join(path, target))
        if not os.path.exists(resolved):
            errors.append(f"{rel}/SKILL.md: broken reference '{target}'")
        elif os.path.commonpath([resolved, unit_dir]) != unit_dir:
            errors.append(f"{rel}/SKILL.md: reference '{target}' escapes unit '{unit}'")


def check_files(errors):
    for base, dirs, files in os.walk(SKILLS):
        dirs[:] = [name for name in dirs if not name.startswith(".")]
        for name in files:
            path = os.path.join(base, name)
            rel = os.path.relpath(path, ROOT)
            if os.path.islink(path):
                errors.append(f"{rel}: symlinks are not allowed")
                continue
            if name.startswith(".env") or name == ".DS_Store":
                errors.append(f"{rel}: must not be committed")
            if os.path.getsize(path) > MAX_BYTES:
                errors.append(f"{rel}: exceeds {MAX_BYTES} bytes")


def main():
    errors, warnings = [], []
    if not os.path.isdir(SKILLS):
        print("ERROR: skills/ directory is missing", file=sys.stderr)
        return 1

    units = visible_dirs(SKILLS)
    if not units:
        errors.append("skills/: no units found")

    seen = {}
    for unit in units:
        unit_rel = os.path.join("skills", unit)
        unit_dir = os.path.join(SKILLS, unit)
        children = visible_dirs(unit_dir)
        has_own = os.path.isfile(os.path.join(unit_dir, "SKILL.md"))

        if has_own:
            members = [unit_rel]
            for child in children:
                if os.path.isfile(os.path.join(unit_dir, child, "SKILL.md")):
                    errors.append(
                        f"{unit_rel}: a skill unit must not also contain the nested skill '{child}'"
                    )
        else:
            members = [
                os.path.join(unit_rel, child)
                for child in children
                if os.path.isfile(os.path.join(unit_dir, child, "SKILL.md"))
            ]
            if not members:
                errors.append(f"{unit_rel}: neither a skill nor a group of skills")
            for member in members:
                for deeper in visible_dirs(os.path.join(ROOT, member)):
                    if os.path.isfile(os.path.join(ROOT, member, deeper, "SKILL.md")):
                        errors.append(f"{member}/{deeper}: nesting deeper than one group level")

        for member in members:
            name = os.path.basename(member)
            if name in seen:
                errors.append(f"duplicate skill name '{name}': {seen[name]} and {member}")
            else:
                seen[name] = member
            check_skill(member, errors, warnings)

    check_files(errors)

    for warning in warnings:
        print(f"WARN  {warning}")
    for error in errors:
        print(f"ERROR {error}", file=sys.stderr)

    if errors:
        print(f"\n{len(errors)} error(s)", file=sys.stderr)
        return 1
    print(f"OK    {len(units)} unit(s), {len(seen)} skill(s), {len(warnings)} warning(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
