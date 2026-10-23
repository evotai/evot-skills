# Android application artifacts

Adapted from the official Android playbook; see [upstream](../UPSTREAM.md). Check the installed CLI's advertised commands, provider implementation and host requirements before selecting this lane. A skill installation alone cannot add capabilities to an older release.

The upstream Android code provider uses a headless JADX **MCP JAR** and Java. That bridge-dependent provider is **not enabled in this CLI-only profile**, even when REA exposes a shell command for it. Do not register it, configure its JAR, invoke JADX directly or claim code inspection succeeded without it. Report this limitation; use another REA-supported non-MCP provider only if the installed release explicitly supplies one.

Archive/member inventory is a separate lane: `rea inspect-artifact` can inspect an APK as a package when supported, without claiming method decompilation or launching the APK. Signature inspection is also separate from code analysis. Keep each operation's availability and coverage explicit.

If a permitted Android code backend is available in a later release, follow the official ordering: package identity/manifest first, class search, one class's members, exact method/overload selection, then incoming references. Choose the overload from returned inventory rather than guessing. Check each command's actual CLI help/schema; underscore-style upstream operation names are not shell commands.

Manifest entries and decompiled text are static observations, not execution or policy enforcement. Incoming references are recovered static relationships; reflection, dynamic loading, and unresolved calls remain unknown. Preserve artifact digests, locations, diagnostics, and incomplete coverage.
