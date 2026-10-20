# Guide catalog and folder map

Start at the [Application Workflow README](../README.md). Read the guides for your selected features; saved choices determine which tools the agent may use. Each procedure begins with its requirements and computer-use needs.

## Set up and run

| Guide | What it does | Required access |
| --- | --- | --- |
| [Onboarding](../ONBOARDING.md) | Choose features, tracker, delivery and schedules. | Codex on macOS + Python; selected tools only. |
| [Main run](../run.md) | Coordinate independent research, save to one tracker, track and report. | Codex + selected tools; main is the sole writer. |
| [Email helper](../helpers/email-discovery.md) | Read alerts and verify official job descriptions. | Gmail reads; browser as needed. |
| [Portal helper](../helpers/referral-portals.md) | Search chosen companies while preserving referral holds. | Public web tools; computer use for interactive pages. |
| [Rated target companies](../blind.md) | Search a private company list under its fit policy; queue results for the same writer. | Public web tools; computer use as needed. |

The two helpers work on the main chat's assignments and have no timers. Rated-company research can have its own selected schedule; queued findings wait for the main chat to save them.

## Selected features

| Guide | What it does | Required access |
| --- | --- | --- |
| [LinkedIn alert setup](linkedin-alerts.md) | Create alerts, filter mail outside Inbox and verify delivery. | LinkedIn computer use + mailbox settings; automated ingestion uses Gmail. |
| [Referral setup](referrals.md) | Connect a private company list to the watchlist and portal registry. | Selected tracker + local helpers. |
| [Tracking](tracking.md) | Track applications and interviews from selected evidence. | Selected Gmail, Calendar or Messages tools. |
| [Messages](messages.md) | Read scoped conversations and existing transcripts when exposed. | Mac + Messages MCP + database permission. |
| [Reports](report.md) | Deliver accepted changes and source gaps. | Configured chat; native Gmail send/Sent read for opted-in self-email. |

## Tracker and evidence procedures

| Guide | Authoritative procedure |
| --- | --- |
| [Local Excel](local-excel.md) | Create, update and verify the private workbook using Codex's spreadsheet runtime. No Excel desktop app or Google access required. |
| [Google Sheets](sheets-protocol.md) | Prepare, authorize and verify native connector writes. No computer use required. |
| [Native evidence](native-evidence.md) | Capture tool evidence, assemble complete Google snapshots, bootstrap a blank template and bind resources. |
| [Shared handoffs](handoffs.md) | Seal research packets, verify producer staging and import through one queue. |
| [Upgrade and recovery](upgrade-and-recovery.md) | Resume interrupted setup/research and reconcile uncertain writes or delivery. |

## Setup and maintenance references

| Guide | Use it for |
| --- | --- |
| [Tools](tools.md), [agent setup](agent-setup.md) | Connection links, selected dependencies and the setup sequence. |
| [Change preferences](preferences.md) | Apply choices while preserving history/bindings; run any required replacement pilot. |
| [Operations](operations.md) | Permissions, one-writer ownership, mandatory start checks, source gaps and completion rules. |
| [Verification](verification.md), [support](../support/README.md) | Offline checks, live-check limits and local code. |
| [Manual actions](optional/manual-actions.md), [Outlook alert routing](optional/outlook-alerts.md) | Separately requested browser actions, or mailbox organization outside the Gmail ingestion path. |

## Where things live

| Folder or file | Purpose |
| --- | --- |
| [helpers/](../helpers/) | Email and referral research instructions. Separate source checks feed one central writer. |
| [docs/](.) | Detailed feature, setup, evidence and recovery procedures indexed above. |
| [sheets/](../sheets/) | Shareable blank tracker and seven-tab schema, including the shared Jobs tab. |
| [support/](../support/README.md) | Setup, queue, journals, writes, receipts and verification code. [Toolkit](../support/toolkit/README.md) parses/checks source evidence; it has no account connections. |
| [blind-companies.json](../blind-companies.json) | Sanitized 103-company starting list. User-supplied ratings are historical, not freshly verified; original dates are unknown. |

Onboarding copies selected targets privately. The [fictional rated-company example](../support/config/examples/rated-companies.json) shows the same format. Personal profiles, working lists/notes, accounts, contacts, chat IDs, schedules and history stay outside the repository.
