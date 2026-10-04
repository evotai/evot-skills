---
name: opencli
description: "Use OpenCLI for browser automation, websites, logged-in web apps, Twitter/X, Hacker News, search, extraction, and external CLI adapters. Trigger on: browse, open page, click, fill form, extract page, Twitter/X, Hacker News, or web search. For Feishu/Lark, use a dedicated lark skill when available; otherwise use OpenCLI."
license: Apache-2.0
compatibility: Requires opencli (npm @jackwener/opencli, Node.js >= 21); browser tasks also need Chrome with the OpenCLI extension
metadata:
  evot:
    requires:
      bins: [opencli]
---

# OpenCLI

OpenCLI exposes websites, browser sessions, web apps, desktop apps, and registered tools as CLI commands.
Use it when a site/app/service can be operated through an OpenCLI adapter or the browser bridge.

## Basic flow

1. Check the binary first:

```bash
command -v opencli
```

If missing, check Node.js:

```bash
node -v
```

If Node.js is available and major version is >= 21, ask for explicit permission before installing OpenCLI globally. Explain that this mutates the user's global npm environment. After approval, run:

```bash
npm install -g @jackwener/opencli
command -v opencli
opencli doctor
```

If permission is declined, or Node.js is missing or older than 21, stop and report the prerequisite instead of installing anything.

2. Discover live capabilities:

```bash
opencli list -f json
opencli <adapter> -h
opencli <adapter> <command> -h
```

3. Prefer a matching adapter when present. `opencli browser` is the last resort, not the default.
4. Prefer structured output (`-f json`) when supported.
5. Do not guess command names or flags; use live help.

## Window policy (do not pop Chrome in the user's face)

OpenCLI has no headless mode: browser work always runs in the user's real Chrome through the extension, sharing its cookies and logins. `opencli browser` defaults to a **foreground** window that steals focus. With `--window background`, OpenCLI opens its own separate automation window: the user's existing windows and tabs are left untouched and focus stays where it was. There is no option to add a tab inside the user's own window; the automation window is the isolation boundary. Follow these rules:

- Every `opencli browser <session> ...` call MUST carry `--window background` unless the user explicitly asks to watch or interact with the page (login, CAPTCHA). `OPENCLI_WINDOW=background` may already be set in the environment; pass the flag anyway.
- Reuse one stable `<session>` name for the whole task so the tab lease is reused instead of re-created.
- Need several pages at once? Use `opencli browser <session> tab new <url> --window background`. The tab opens in the automation window (not the user's), prints a `page` id, and becomes the session's default tab. Switch with `tab select <id>` or `--tab <id>`, and close it with `tab close <id>`.
- Never navigate, click in, or close a tab the session did not create, unless the user asked you to work in that tab.
- Only use `--window foreground` when the user must act in the page; say so before doing it.
- `OPENCLI_CDP_ENDPOINT` does NOT redirect `opencli browser` or site adapters (it only applies to Electron app adapters). Do not try to route browser commands to a headless Chrome with it.

### `bind` drives the user's own tab

`opencli browser <session> bind` takes no URL or domain: it attaches to whichever tab is **currently focused** in Chrome, then every `open`/`click`/`type` runs in that tab. It does not open a window, but it does act on the page the user is looking at. Only use it when the page's state can't be reached any other way (for example, a page in the middle of an SSO flow or a form the user already filled in). Before binding, ask the user to focus the target tab. Prefer read-only commands (`state`, `get`, `extract`) and run `unbind` when done; `unbind` detaches without closing the tab. For an ordinary logged-in site, use `open --window background` instead: the automation window shares the same cookies.

## Browser dependency

Only check/install browser support when the selected path needs it:

- `opencli browser ...`
- logged-in cookies or session state
- page UI automation, clicking, forms, extraction from a live tab
- adapters whose live metadata/help shows `COOKIE`, `INTERCEPT`, or `UI` strategy

For `PUBLIC` or `LOCAL` adapters, do not require the Chrome extension.

When browser support is needed, run:

```bash
opencli doctor
```

If the browser bridge or Chrome extension is unavailable, stop browser-dependent execution and ask before opening the extension install page. After approval, use the platform-appropriate command:

```bash
# macOS
open "https://chromewebstore.google.com/detail/opencli/ildkmabpimmkaediidaifkhjpohdnifk"
# Linux
xdg-open "https://chromewebstore.google.com/detail/opencli/ildkmabpimmkaediidaifkhjpohdnifk"
```

Then ask the user to click "Add to Chrome", enable the extension, keep Chrome running, log into the target site if needed, and retry. Do not attempt to install the extension silently.

Do not ask the user to export cookies. For cookie/session tasks, run commands in the bound browser context instead.

## Common routing hints

Confirm names with `opencli list -f json` before use.

- `browser`: ordinary websites, logged-in pages, clicking, forms, extraction.
- `twitter`: Twitter/X timelines, search, posts, profiles, notifications.
- `feishu` / `lark` / `lark-cli`: chats, messages, docs, search, sending.
- `hackernews`: stories and discussion search.
- `github`: repositories, issues, PRs, code lookup.
- `google` or search adapters: broad web lookup.

## Feishu / Lark priority

For any Feishu or Lark task (messages, groups, docs, calendar, contacts, etc.), use an available dedicated `lark-*` skill first. If no matching skill is available, prefer `opencli lark-cli` over browser-based access. The `lark-cli` adapter provides structured API access that is faster, more reliable, and does not require browser/extension setup.

When falling back to OpenCLI, try this first:

```bash
opencli lark-cli --help
opencli lark-cli <subcommand> --help
```

Key subcommands: `im` (messages/groups), `docs` (documents), `calendar`, `contacts`, `drive`.
Only fall back to `opencli browser` for Feishu if `lark-cli` is unavailable or the specific operation is not supported.

## Browser workflow

`opencli browser` requires a `<session>` positional right after `browser`. Pick one name per task and reuse it.

For a new page (background window, no focus steal):

```bash
opencli doctor
opencli browser work open <url> --window background
opencli browser work state --window background
opencli browser work extract --window background
opencli browser work close --window background   # release the session's tab lease
```

More pages in the same automation window:

```bash
opencli browser work tab new <url> --window background    # prints {"page": "<id>"}
opencli browser work tab list --window background
opencli browser work extract --tab <id> --window background
opencli browser work tab close <id> --window background
```

Only when the user has focused the exact tab to work in (see `bind` above):

```bash
opencli browser work bind      # attaches to the currently focused tab
opencli browser work state
opencli browser work unbind    # detach; never closes the user's tab
```

Use `state`, `find`, `click`, `type`, `keys`, `get`, and `extract`. Refresh state after navigation or major DOM changes. Do not reuse stale refs. Run `opencli browser <session> close` at the end of a task to release the lease. `close` may leave an empty automation window behind (its tabs are reset to `about:blank`). That's harmless, but never close Chrome windows yourself to clean it up.

## Safety and failures

Reading, searching, listing, and extracting are usually safe. Sending, posting, liking, deleting, editing, following, purchasing, settings changes, and mutating SQL are mutations.

If a command fails: read the error, check live help/strategy, run `opencli doctor` for browser-dependent tasks, and retry only when the fix is clear. Report missing installation, missing extension, login, CAPTCHA, rate limit, or API failure directly.

Do not expose credentials, cookies, tokens, or private browser data. Do not invent data when OpenCLI cannot retrieve it.

Final answer: report the result, not the mechanics; mention sources/pages only when helpful.
