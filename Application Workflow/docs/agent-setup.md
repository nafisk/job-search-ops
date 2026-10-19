# Agent setup reference

> **Required:** Codex desktop on macOS, Python 3.10+, a permanent checkout, private writable state and the user's selected features. See [tools](tools.md).
> **Runs in:** Codex app with the tools required by those choices.
> **Computer use:** Selected browser setup and user-handled sign-in/permission prompts.

Follow [onboarding](../ONBOARDING.md) interactively and use the shared [operating rules](operations.md). The user chooses features; the assistant prepares settings and runs checks. Do not ask the user to edit JSON or present every possible question at once. Run helper commands from `Application Workflow/support/`; workbook assets are in `Application Workflow/sheets/`.

## 1. Establish the selected workflow

Read this installation's existing private preferences, permissions and resource receipts before asking questions. Never use another person's deployment as a default. Keep the repository permanent and personal state outside it, outside disposable chat folders. Preserve an existing authoritative resume at its chosen location.

Proceed through tracker, discovery, tracking, execution and delivery choices one at a time. Ask relevant follow-ups while that choice is in view. Reuse valid saved answers; ask only where a choice is absent, conflicts with the current request, or changes an effect. Manual execution and chat reporting are defaults.

| Choice | Relevant follow-ups |
| --- | --- |
| Local Excel or Google Sheets | Local private `.xlsx` path, or Google account/workbook title/destination. One tracker only. |
| Email alerts, portals, Blind, or no discovery | Job/location criteria and truthful resume facts; [LinkedIn alerts, delivery and inbox routing](linkedin-alerts.md), email queries/lookback only for alerts; referral companies/holds only for portals; rated list/provenance/threshold only for Blind. |
| Gmail, Calendar, Messages tracking, or none | The selected account/calendar/conversation and initial window. Calendar and Messages do not require Gmail. |
| Manual or scheduled execution | Timezone for all displayed dates; times and notification preferences only for requested main/Blind schedules. Helpers never get timers. |
| Chat or self-email | Ask recipient and explicit send opt-in only for email. |

For a new installation, choose an existing durable parent outside the repository and create a dedicated private installation directory with owner-only permissions (`0700`). Save draft settings and copied source files with owner-only permissions (`0600`). Check existing ownership/permissions before reusing a directory; do not overwrite another installation.

Use **`draft-config.json` and `draft-profile.json`** for the initial inputs. Set the draft config's `profile_path` to the draft profile and `instance_root` to the selected private directory. Reserve **`config.json` and `profile.json` for the normalized snapshots created by `init`**; writing raw drafts under those names can fail initialization. Keep this setup location durable, including when runs are manual.

When rated target companies are selected, offer the [sanitized 103-company starter](../blind-companies.json) or the user's own list. Explain that ratings are historical, user-supplied and not freshly verified, with unknown original dates. Copy the selected list into the user's private installation area, review enabled targets, then bind its absolute path as `sources.rated_companies_path`; repository paths are rejected by the validator. Preserve `rating_origin: "user_supplied"` and `rating_as_of: "unknown"` unless actual provenance supports a different value. Recheck career URLs during research. Do not replace existing private targets, add personal notes to the repo, or enable Blind solely because the starter exists.

Do not assume the example's targets, experience, company list, accounts or schedule choices. Discovery targets and applicant qualifications are separate facts. Tracking-only configurations need no discovery lists or helper chats. Public-only/local-Excel/chat configurations need no Google account. Do not collect unused contacts, inbox permissions or resumes merely because an example has a field. If no discovery or tracking source is selected, explain that no work has been chosen and resolve that choice before setup.

When LinkedIn email discovery is selected, run the [separate alert setup check](linkedin-alerts.md) before freezing email queries. Save selected searches/routing intent in a private draft before external changes. Verify desired job searches, email delivery and a narrow label/filter that skips the inbox; reuse existing matches. The guide covers manual settings when a native setup tool is absent and distinguishes Outlook organization from this release's Gmail reader. Transfer/reference the private draft as `evidence/linkedin-alerts-setup.md` after initialization, keeping planned queries, user-confirmed settings and tool-observed results distinct. Do not invent sender queries, add unsupported settings fields or pretend a zero-result mailbox query proves alerts work.

Prepare a v2 private configuration using the [installation example](../support/config/examples/installation-v2.json) and [profile example](../support/config/examples/profile-v2.json) as structure only. Its branch choices are `tracker.provider` (`local_xlsx` or `google_sheets`), `tracker.path` (local absolute path or null for Google), `discovery.email`, `discovery.portals`, `tracking.gmail`, and the existing `modules.blind`, `modules.calendar`, `modules.messages`. Central remains enabled. Save the user's chosen preferences before any resource creation or external setup.

```sh
python3 -m job_search_ops setup-plan --config /absolute/private/draft-config.json
```

This read-only plan is the canonical list of selected tracker, sources, chats, files, schedules and permissions. Show that concise summary to the user before proceeding. It is not evidence that the operations work. The user's request to set up the features they choose is sufficient authorization for those resources and pilot; do not add another blanket approval gate. Ask only when a necessary choice or authorization is genuinely missing. New installs, connections, credential flows and permission expansions are separate actions, never silent consequences of the plan.

## 2. Check only the selected requirements

Use [tools](tools.md) to inspect the actual capabilities. Distinguish selected, installed, connected, and authorized for the operation. A visible tool does not prove the right identity, scope or write permission. Check the required interpreter and private paths; use existing supported tools first.

Local Excel requires the app-provided Node/spreadsheet editing runtime as well as Python. Discover it through `load_workspace_dependencies`, read the installed spreadsheet skill, and follow its required operation-start step before the first workbook create/edit. Do not install the private artifact package from public npm or substitute an unverified writer.

Gmail reads are needed for selected email alerts or Gmail tracking. Gmail sending/Sent readback is needed for self-email. Drive/Sheets is needed only for the Google tracker. Calendar and Messages checks are needed only for selected tracking sources. Public job research is needed only for selected discovery. Do not make any of these requirements global.

```sh
python3 -m job_search_ops init --config /absolute/private/draft-config.json
python3 -m job_search_ops doctor --config /absolute/private/config.json
```

After `init` succeeds, use the generated `/absolute/private/config.json` for subsequent commands; it points to the normalized `profile.json`. Reuse those canonical files on restart. Editing drafts later does not update an initialized installation; follow [the preferences update process](preferences.md) for changed choices.

Initialization creates private local state, not cloud resources. Preserve existing journals on rerun. Selected unavailable sources stay unavailable; unselected sources are not setup failures. Continue independent permitted work, but do not mark the affected operation verified or enable its dependent schedule.

`doctor` does not inspect LinkedIn subscriptions or mailbox rules. Complete the alert guide's separate received-message/routing check for selected LinkedIn discovery. Setup-only label/filter changes require actual supported tools and the user's selected scope; daily email discovery remains read-only.

## 3. Create or bind the chosen tracker

Use existing verified bindings on restart. Record intent before creating a resource; reconcile unknown outcomes before trying again. Never overwrite an existing workbook or reuse a different live deployment automatically.

**Local Excel:** follow [the local Excel protocol](local-excel.md) to initialize the private workbook, record its identity and verify real saved file contents. Keep it authoritative; do not create a Google copy. Check actual path access and the backend's concurrency/recovery rules. Merely copying an XLSX template or exporting data does not prove future saves work. No Google resource evidence is required for this branch.

**Google Sheets:** follow [the Sheets protocol](sheets-protocol.md) and [native evidence](native-evidence.md). Reserve the tracker resource with `resource-intent`, import the checked-in blank `../sheets/job-search-tracker.xlsx` through the native Drive connector, then assemble actual metadata/CellData with `snapshot`. Generate the empty-workbook setup requests with `bootstrap` and apply them through `batch_update_spreadsheet` once. Retain its actual `updatedSpreadsheet`, including grid properties, basic filters, column metadata, validation, dates and summary formulas. Verify all seven tabs, row-4 headers and hidden Job Key before `resource-record`. IDs and links must come from the actual provider. The daily minimal cell mask alone cannot prove setup formatting or hidden columns. Bootstrap uses basic filters, not native Tables.

Both backends use the shipped schema, stable job identities, exact links, preserved manual fields and accepted-save receipts. Import only the selected user's reviewed company/referral inputs. Keep private correspondence out of tracker notes. Use the bound runtime profile for toolkit operations; the input profile is not proof of a live tracker.

If portal discovery is selected, complete [referral company setup](referrals.md) now. Copy the fictional source format privately, populate the chosen tracker’s watchlist with the `referrals-*` commands and verify `<installation>/portal-registry.json` before accepting the portal pilot. The private company list defines scope; stricter manual holds remain protected.

## 4. Create only the selected chats

The setup plan determines the bindings: central always; email iff email discovery; portals iff portal discovery; Blind iff Rated target companies. Tracking runs centrally and adds no helper. Use `create_thread` under the setup authorization; use `list_projects` first if choosing a repository project. Inspect existing receipts before creating replacements.

Record each actual chat ID and verify its writable workspace. Run `prompts --config ...` after required bindings exist; generated prompts must contain real IDs and permanent absolute paths. Preserve explicit delegation authorization for selected helpers and any selected producer-to-central handoff. If messaging is unavailable, report that dependent gap; do not silently create a different topology.

Producers may have narrower filesystem access. Use the [sealed handoff](handoffs.md#producer-handoff): they save in a verified writable workspace; central verifies/copies/enqueues when the shared queue is inaccessible. Keep staging until archival is acknowledged. Never restart successful research merely because archival is pending.

## 5. Pilot the selected path

Use a small declared scope for each selected source. Skip unselected branches entirely. A tracking-only pilot checks its selected tracking sources and tracker/report path, without inventing discovery jobs. If no real role qualifies, record that honestly; fixtures must not be inserted as live jobs.

For LinkedIn alerts, verify a genuine alert received after rule creation, its destination outside Inbox, and full-message access through the configured Gmail queries. A read or archived message must still be discoverable. If delivery is pending, retain `awaiting_first_alert`; do not accept the email pilot or enable its dependent schedule. Independent selected branches can proceed.

Exercise the selected backend's save/readback, duplicate protection and manual-field preservation with actual accepted evidence when available. Confirm queued results remain distinct from saved results. Verify a real report through the selected delivery channel; a preview is not delivered. Record the selected first pass using `first-pass-record` and actual evidence. See [native evidence](native-evidence.md) for connector observations and [local Excel](local-excel.md) for file evidence. Offline tests and asserted success flags cannot replace these checks.

## 6. Finish manually or enable chosen schedules

For manual mode, create no automation intents and request no scheduling access. Give the user the central chat and a short run instruction. Manual Blind output stays pending until central imports it; explain this without adding a timer.

Only for requested schedules, run `schedule-plan` after required selected checks and first passes are verified. Use `automation_update` to create/read back the chosen main and/or Blind thread heartbeats at the user's times/timezone. Helpers stay unscheduled. Preserve notification preferences and existing unrelated automations; never substitute shell cron. A scheduled Blind source does not itself save rows or schedule central.

Finish with the actual tracker path/link, selected chats, how to run manually, chosen schedules if any, private state location and unresolved checks. Do not claim full setup while a required selected effect remains unverified.
