# Selected tools and permissions

> **Required for the core:** Codex desktop on macOS, Python 3.10+, a permanent checkout and private writable state.
> **Runs in:** Codex app; the matrix below adds requirements only for selected features.
> **Computer use:** A supported browser is required for discovery; actual interaction depends on the page. Signed-in browser access is required only for selected authenticated tasks.

[Onboarding](../ONBOARDING.md) determines the features; `setup-plan --config ...` determines their dependencies. This inventory is the assistant's reference, not a list every user must install. Commands run from `Application Workflow/support`.

**Selected**, **installed**, **connected to the expected identity**, and **authorized for the requested operation** are separate facts. Check actual saved preferences and tool responses. Do not turn a tool's availability into permission to use an unselected source.

## Shared requirements

Use the local Codex desktop host, a permanent checkout and private writable state. Python 3.10+ runs the included helpers with standard-library/POSIX locking and IANA timezone data. Check existing tools first; [Python downloads](https://www.python.org/downloads/) are relevant only when a compatible runtime is missing. The supported workflow targets a local Mac; Windows/cloud execution is not certified.

The central chat always coordinates the selected work. Other chats, browser access, Google connections and scheduling capabilities are conditional. Keep the local computer/app available only when relying on local scheduled execution; manual mode needs no automation setup.

## Capability branches

| Selected feature | Needed capability and allowed scope |
| --- | --- |
| Local Excel tracker | Private `.xlsx` path, the shipped [local workbook backend](local-excel.md), and app-provided Node/spreadsheet editing runtime discovered with `load_workspace_dependencies`. Verify actual file reads/writes, identity, schema and readback. No Drive/Sheets connection or Google workbook is needed. |
| Google Sheets tracker | Native Google Drive/Sheets identity, import, metadata/CellData read and checked batch writes. Verify the account, selected workbook, seven-tab schema, links and manual-field preservation. |
| Email alerts | Gmail identity, labels/search, full message/MIME reads and pagination. No mail mutations. |
| Referral portals or Blind | Public search/open, official pages and a supported public HTTP/browser reader. Optional [curl](https://curl.se/download.html) is unnecessary when a native reader works. Verify scope, pagination and exact job details. |
| Gmail tracking | Gmail reads for exact-role receipts, replies and Sent history. Independent of email-alert discovery; no mail mutations. |
| Calendar tracking | Native Google Calendar connection, selected calendars, bounded event search/read and identity checks. No booking, RSVP or event changes. |
| Apple Messages tracking | macOS, connected Mac Messages MCP, user-granted database access, an explicitly selected conversation and reviewed read tools. See [Messages setup](messages.md). No bundled MCP server/decoder; no sends, contact edits or availability probes. |
| Self-email report | Explicit recipient/send opt-in, Gmail sending and actual Sent search/readback. Chat reports need no send capability. |
| Scheduled runs | App automation create/view/readback for the chosen central and/or Blind chat only, after verified pilot. Manual mode creates no timers. |

For Google features, [connect the relevant plugin](https://learn.chatgpt.com/docs/plugins) and start a fresh chat when needed. Use native connectors; do not install `gws`, extract cookies or create alternate OAuth to bypass missing access. A local-Excel/public-research/chat/manual configuration needs neither Google Drive nor Gmail.

## Native tools and optional additions

[LinkedIn alert onboarding](linkedin-alerts.md) adds a one-time setup step only when that source is selected: inspect/create the chosen alerts through the supported signed-in LinkedIn browser, and inspect/create the selected mailbox label/filter where actual native tools support it. Gmail `create_label` does not establish filter-management support. If a native Gmail filter tool is absent, the user creates the rule in Gmail settings and the assistant verifies delivery with native reads; no alternate Google credentials or browser access is introduced. Outlook folder/rule setup uses selected supported controls, but this release's automated reader is Gmail-only. No new CLI, MCP server, permanent helper chat or schedule is required for alert setup. Record subscription/delivery/routing proof separately from `doctor` tool receipts; daily discovery never inherits mailbox mutation permissions.

Discover current schemas instead of assuming exact provider arguments. Relevant Google operations include profile reads, Gmail search/read/send as selected, Drive `import_spreadsheet`, `get_spreadsheet_metadata`, `get_spreadsheet_cells` and `batch_update_spreadsheet`. Calendar uses bounded search and event reads.

Chat operations use `list_projects`, `create_thread`, `read_thread`, `send_message_to_thread` and `wait_threads` for selected bindings and authorized delegation. `automation_update` is used only for selected schedules. Optional collaboration tools can verify disjoint work; they do not create an obligation to add more permanent chats.

Public research may use supported `mcp__cua_repl.js` controls. Authenticated Chrome is optional when a selected access path needs it or the user separately requests manual application/recruiter work. Follow the [supported browser connection](https://learn.chatgpt.com/docs/chrome-extension), verify the session and preserve user tabs. Never autofill, upload resumes, apply or send outreach automatically. Serialize controls unless the host demonstrates safe isolation.

This release supports Messages through the [external Mac Messages MCP](https://github.com/carterlasalle/mac_messages_mcp) and its reviewed read tools. Follow [Messages setup](messages.md) and [Codex registration](https://learn.chatgpt.com/docs/extend/mcp) only when selected. Other Messages plugins are not assumed compatible; they need their own reviewed tool/evidence mapping before use. Missing transcript support is a source gap, not a requirement to build a decoder.

## Checks and maintenance

Run `doctor` against selected requirements (`--workflow main` or `--workflow blind`
for an individual schedule). Run the [execution check](operations.md) before each
workflow accesses sources; pending preference pilots hold only affected work.
Then preserve actual file/native evidence for the intended effects. Offline fixtures, tool catalogs and manually asserted flags do not prove live saves or delivery. Unselected sources are not missing dependencies; selected unavailable sources remain disabled/partial with their dependent work held.

Git and shell utilities are operator conveniences. Local Excel authoring, rebuilding the blank template or explicitly exporting XLSX uses the app-provided Node/spreadsheet runtime discovered through `load_workspace_dependencies` and the installed spreadsheet skill. Follow that skill’s operation-start requirement before authoring. Google setup imports shipped assets without a rebuild; never install the private artifact package from public npm or copy another user's cache. Personal skills, Beautiful Soup, Node Simplify decoding, browser automation libraries and custom Messages binaries are not default requirements.

Do not install software, add credential flows or expand permissions automatically. Update the [capability manifest](../support/config/capabilities.json) when deliberately introducing a new dependency. Keep configuration and history private, and state which selected live checks remain unverified.
