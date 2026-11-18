# Selected tools and permissions

Choose features in [onboarding](../ONBOARDING.md) and inspect their dependencies with `setup-plan --config ...`. Run commands from `Application Workflow/support`. See [repository onboarding](../../ONBOARDING.md#tools-for-your-choices) for common tools.

For each selected operation, verify that the tool is installed, connected to the expected identity and authorized for that operation. Sign in to the browser only for selected authenticated work.

## Workflow requirements

The helpers use Python's standard library, `fcntl` file locking, and IANA timezone data. The agent needs access to the checkout and private installation. Check the selected tools and run a scoped pilot before relying on another host.

The central chat always coordinates the selected work. Other chats, browser access, Google connections and scheduling capabilities are conditional. For a local schedule, keep the machine and runner available. Manual runs need no scheduler.

## Capability branches

| Selected feature | Needed capability and allowed scope |
| --- | --- |
| Local Excel tracker | Private `.xlsx` path, the shipped [local workbook backend](local-excel.md), and a compatible Node runtime with `@oai/artifact-tool`. Verify actual file reads/writes, identity, schema and readback. No Drive/Sheets connection or Google workbook is needed. |
| Google Sheets tracker | Native Google Drive/Sheets identity, import, metadata/CellData read and checked batch writes. Verify the account, selected workbook, seven-tab schema, links and manual-field preservation. |
| [Discovery export](discovery-export.md) | Local Excel uses the same spreadsheet runtime as the Excel tracker. Google Sheets uses the connected account, native import, metadata and checked batch writes on the separate export workbook. |
| Email alerts | Gmail identity, labels/search, full message/MIME reads and pagination. No mail mutations. |
| Referral portals or [Blind research](<../../Blind Company Research/run.md>) | Public search/open, official pages and a supported public HTTP/browser reader. Optional [curl](https://curl.se/download.html) is unnecessary when a native reader works. Verify scope, pagination and exact job details. |
| Gmail tracking | Gmail reads for exact-role receipts, replies and Sent history. Independent of email-alert discovery; no mail mutations. |
| Calendar tracking | Native Google Calendar connection, selected calendars, bounded event search/read and identity checks. No booking, RSVP or event changes. |
| Apple Messages tracking | macOS, connected Mac Messages MCP, user-granted database access, an explicitly selected conversation and reviewed read tools. See [Messages setup](messages.md). No bundled MCP server/decoder; no sends, contact edits or availability probes. |
| Self-email report | Explicit recipient/send opt-in, Gmail sending and actual Sent search/readback. Chat reports need no send capability. |
| Scheduled runs | App automation create/view/readback for the chosen central and/or Blind chat only, after verified pilot. Manual mode creates no timers. |

For selected Google features, use the [shared capability checklist](../../ONBOARDING.md#tools-for-your-choices) and start a fresh chat when needed. Use native connectors. Do not install `gws`, extract cookies or create alternate OAuth to bypass missing access. A local-Excel/public-research/chat/manual configuration without a Google export needs neither Google Drive nor Gmail.

## Native tools and optional additions

Use [LinkedIn alert setup](linkedin-alerts.md) to check alert creation, mailbox routing, and real delivery. The [email runbook](../helpers/email-discovery.md) covers routine Gmail reads.

Discover current schemas instead of assuming exact provider arguments. Relevant Google operations include profile reads, Gmail search/read/send as selected, Drive `import_spreadsheet`, `get_spreadsheet_metadata`, `get_spreadsheet_cells` and `batch_update_spreadsheet`. Calendar uses bounded search and event reads.

Check that the agent can create or reuse the selected sessions, read their output, and hand work to authorized helpers. Check scheduler controls only when scheduling was selected. The [capability manifest](../support/config/capabilities.json) lists the tool identifiers recognized by the bundled evidence checker.

Use the agent's public page reader or browser controls for research. For a selected signed-in task, verify the authorized browser profile and preserve user tabs. Never autofill, upload resumes, apply or send outreach automatically. Serialize controls unless the host demonstrates safe isolation.

This release supports Messages through the [external Mac Messages MCP](https://github.com/carterlasalle/mac_messages_mcp) and its reviewed read tools. Follow [Messages setup](messages.md) when selected. Other Messages plugins are subject to compatibility checks. They need their own reviewed tool/evidence mapping before use. Missing transcript support is a source gap, not a requirement to build a decoder.

## Checks and maintenance

Run `doctor` against selected requirements (`--workflow main` or `--workflow blind`
for an individual schedule). Run the [execution check](operations.md) before each
workflow accesses sources; pending preference pilots hold only affected work.
Then preserve actual file/native evidence for the intended effects. Offline fixtures, tool catalogs and manually asserted flags do not prove live saves or delivery. Unselected sources are not missing dependencies; selected unavailable sources remain disabled/partial with their dependent work held.

Use the [Excel writer runtime](local-excel.md) to edit or rebuild an XLSX. Google setup imports the shipped workbook as a native Sheet. Use only the dependencies needed for the selected features.

Do not install software, add credential flows or expand permissions automatically. Update the [capability manifest](../support/config/capabilities.json) when deliberately introducing a new dependency. Keep configuration and history private, and state which selected live checks remain unverified.
