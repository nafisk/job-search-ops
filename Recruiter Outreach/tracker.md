# Recruiter storage and recovery

> **Required:** A private folder outside the repository, Python 3.10+ with its standard library and one selected tracker: local JSON or native Google Sheets. Google mode also needs the expected Google account and checked workbook access.
> **Runs in:** Codex local files/terminal and selected Google tools. No bundled database, server or script installation.
> **Computer use:** Not required for ordinary tracker reads/writes; required separately to verify actual LinkedIn profiles and drafts.

Use a **separate recruiter tracker**. The Application Workflow jobs workbook has a different schema and does not store these records. Read this guide before creating storage or saving contact/draft history.

## Agent-facing settings

Collect the choices and approved copy in [onboarding](ONBOARDING.md#3-save-your-choices-and-approved-copy), then create private `settings.json` using this starting shape. Replace nulls and empty targets through the setup conversation; they are deliberately incomplete values. Never replace existing settings without reviewing and preserving their choices and history.

```json
{
  "schema_version": 1,
  "setup_status": "needs_setup",
  "timezone": null,
  "browser": {"name": "chrome", "account_identity": null},
  "tracker": {
    "backend": "local_json",
    "spreadsheet_id": null,
    "worksheet": "Recruiters",
    "header_row": 1,
    "expected_google_identity": null
  },
  "targets": {"specialties": [], "candidate_levels": [], "excluded_remits": []},
  "capacity": {"outstanding_drafts": 20, "pilot_drafts": 2},
  "research": {"target_per_company": 25, "read_attempts": 3},
  "channels": ["inmail", "linkedin_message", "connection_note"],
  "allow_needs_review_drafts": false,
  "next_batch_confirms_previous_sent": false,
  "approved_copy": {
    "approved": false,
    "approval_reference": null,
    "subject": "",
    "body": "",
    "connection_note": ""
  }
}
```

Use the chosen IANA timezone and observed account identity. Select one or more allowed channels; an available but unselected channel is not a fallback. Set a positive outstanding-draft ceiling and a pilot count no larger than it. The research count is a configurable goal, not proof of full coverage or a draft quota. Google mode sets `backend` to `google_sheets` and requires the actual workbook ID and expected account. Approved copy must have no unsupported facts or unresolved fact placeholders before drafting.

Save the absolute private folder and repository locations in the assigned operating chat's instructions. Complete the [setup summary](../ONBOARDING.md#your-setup-summary) as an index to authoritative settings and records, not a second configuration.

## Outreach tool checks

Use the [shared tool setup](../ONBOARDING.md#tools-for-your-choices) for general connection guidance, then verify the selected outreach capabilities:

| Capability | Setup and proof |
| --- | --- |
| Codex and local files | Open the permanent checkout in Codex. Confirm Python 3.10+ is available and a private JSON file can be saved and read back. Python's standard library is sufficient; no extra package is needed. |
| Supported browser | Select Chrome or another browser the current host supports using the shared connection guidance above. The user logs into LinkedIn; verify the observed account matches the chosen identity. Preserve unrelated tabs. |
| Google tracker, if selected | Use the selected native Drive/Sheets connection. Read the installed Google Sheets skill before Google access/effects. Verify account identity, access to the exact workbook, metadata/cell reads and narrow writes with readback. Follow the current tool schemas. |
| Research | Use available public search/page reads and the supported LinkedIn browser. Search results find leads; live profiles supply current evidence. |

Standalone outreach uses these checks, not Application Workflow's configuration, `doctor`, start check or capability manifest. Gmail, Calendar, Messages and scheduling are not outreach requirements. Do not install a CLI, email-finder service, extra MCP server or alternate credential flow for this setup. If a selected capability is unavailable, record the missing step and keep setup incomplete; never substitute another account. Access does not grant permission to send.

## Set up storage

Check the private folder's actual filesystem location, including symlinks and case aliases; it must be outside this repository and any shared export folder. Keep one installation per person and never bind another person's contacts or batches.

For a new installation, create private `settings.json` from [the settings reference](#agent-facing-settings) and `state.json` with this exact empty starting shape. On restart or adoption, read existing records first; never initialize over them. Use owner-only `0700` folders and `0600` files, including private snapshots, proofs and temporary replacements:

```json
{
  "schema_version": 1,
  "research_runs": [],
  "batches": [],
  "writes": []
}
```

**Local JSON:** for a new empty tracker, create `contacts.json` beside them:

```json
{
  "schema_version": 1,
  "revision": 0,
  "contacts": []
}
```

This is the contact source of truth. Read and parse it after creation, verifying version, revision and empty contacts. For adoption, verify the existing version, revision, contact fields and identities, history and unresolved drafts instead of requiring empty contacts. Review any required migration before writing; never reset the revision or discard history. Optional `contacts.csv` is a generated view using the columns below; regenerate it from JSON, never overwrite JSON from an unreviewed CSV. Do not open untrusted values as spreadsheet formulas: export literal text and escape formula-leading cells for the selected viewer.

**Google Sheets:** read the installed Google Sheets skill and verify the selected account. Before creation, save a `create_tracker` intent in `state.json` with a unique write ID, expected account, requested title and any tool-supported request/idempotency identifier. Use the native tool's supported create/import operation to create a new blank workbook with a `Recruiters` worksheet. Save the actual returned workbook ID and verify native metadata/readback before binding it. If no creation operation is available, the user creates the empty workbook and supplies its link. Do not introduce alternate credentials. Adopt an existing workbook only after explicit mapping and history review.

If creation returns no ID or times out, retain the intent as `reconciliation_required`. Use the provider's documented operation/idempotency status or inspect the expected account with actual creation evidence to identify the outcome. A matching title, missing return value or one empty search is not enough to create again. If the outcome cannot be established, hold setup for a user-assisted binding; never create a second tracker to bypass uncertainty.

For a newly created blank sheet only, write the exact headers below to `A1:U1` as literal values. Read native metadata and the cells back; verify the exact workbook ID, tab, header row, all 21 header names and initially empty contact rows. For an adopted sheet, verify its reviewed mapping to all 21 fields, stable identities, existing history and unresolved drafts; do not rewrite headers or require empty rows. Save any nonstandard column mapping in the private setup-readback record and use it for every read/write. Missing or ambiguous fields require a reviewed migration before use.

Save the verified workbook/tab/header binding in settings. Read/write only this mapped table. Freeze/filter the header if supported; formatting is optional. No hidden identity hyperlinks, formulas, native table object or Apps Script is required.

In Google mode the sheet is authoritative for contact/history fields; private `state.json` owns batch reservations, detailed evidence, approved copy snapshots and write recovery. Reconcile both before acting. A stale local snapshot cannot overwrite live manual edits. Keep a dated private setup-readback record; do not use a passing JSON parse as proof of Google access.

## Contact fields

Use these JSON keys. New Google sheets and generated CSVs use the exact headers in this order; adopted Google sheets use their verified private field mapping. Every contact has all fields; use `null` for unknown dates, `false` for the initial do-not-contact flag and empty strings only for genuinely empty text. No invented check dates or send history.

| JSON key | Header | Meaning |
| --- | --- | --- |
| `contact_id` | Contact ID | Stable locally assigned ID; never a row number |
| `company` | Company | Reviewed target employer |
| `name` | Name | Observed name |
| `profile_url` | Profile URL | Observed canonical LinkedIn profile URL; dedup key |
| `fit` | Fit | `Match`, `Needs review`, `Exclude` |
| `employer_check` | Employer check | `Verified current`, `Unconfirmed`, `Not current` |
| `qualification` | Qualification | `Qualified`, `Hold: employment`, `Hold: specialty`, `Excluded` |
| `recruiting_scope` | Recruiting scope | Current supported remit |
| `candidate_levels` | Candidate levels | Supported levels or explicitly unspecified |
| `evidence` | Evidence | Source statements, URLs, uncertainties and check references |
| `checked_at` | Checked at | Actual evidence check time with timezone, or null |
| `status` | Status | `Not contacted`, `Queued`, `Sent`, `Followed up`, `Replied`, `Do not contact` |
| `channel` | Channel | `inmail`, `linkedin_message`, `connection_note`, or empty |
| `sent_at` | Sent at | First confirmed send date/time and known precision |
| `follow_up_at` | Follow-up at | Confirmed follow-up date/time and known precision |
| `reply_notes` | Reply notes | User notes, replies and outcomes; preserve existing text |
| `do_not_contact` | Do not contact | Boolean; suppression is independent of fit |
| `draft_state` | Draft state | `none`, `reserved`, `verifying`, `ready`, `needs_review`, `blocked`, `user_confirmed_sent` |
| `batch_id` | Batch ID | Current/last relevant private batch reference |
| `draft_link` | Draft link | Actual persistent draft link if available; otherwise empty |
| `next_action` | Next action | Concrete pending owner/action |

Google cells for unknown dates/text remain blank; `Do not contact` stores a native Boolean. Store all source/user text literally, never as executable formulas. Native browser tab references belong in private batch state even when no persistent draft URL exists.

Qualification is an evidence-backed decision, not an automation: Exclude fit, Not current employer, `do_not_contact: true` or Status = Do not contact means Excluded. Otherwise missing verified employer/evidence means Hold: employment; absent target fit means Hold: specialty; verified employer/evidence plus Match means Qualified. New unread leads start Needs review, Unconfirmed and Hold: employment. Keep all communication history when a company or scope changes. A qualification value alone never substitutes for inspecting evidence.

Normalize profile URLs before deduplication; require identity evidence for alternate URLs and store accepted aliases in the private research record. Never merge on matching names alone. Preserve contact IDs and old employer/history facts when the person's current company changes.

## Private state records

The empty arrays above receive records only when work starts. These are local agent-maintained formats, not an executable API or claim of automatic validation.

| Array | Required record fields |
| --- | --- |
| `research_runs` | `run_id`, `request_reference`, `companies`, `started_at`, `owner`, `status`, `queries`, `coverage`, `contact_evidence`, `accepted_aliases`, `exceptions`, `resume_cursor` |
| `batches` | `batch_id`, `request_reference`, `company_scope`, `target_count`, `created_at`, `owner`, `phase`, `copy_snapshot`, `contacts`, `handed_off_at`, `next_action` |
| `writes` | `write_id`, `operation`, `backend`, `binding`, `contact_ids`, `before`, `intended_after`, `state`, `attempted_at`, `readback`, `next_action`; creation additionally records expected account/title, provider request reference and actual returned ID when available |

Each batch contact stores `contact_id`, `profile_url`, `owner`, `preparation_state`, `identity_locked`, `capacity_occupied`, `channel`, `subject`, `body`, `browser_tab_ref`, `proof_path`, `draft_prepared`, `verified_at`, `handed_off_ready`, `blocker`, `user_send_confirmed` and `send_confirmation`. Use Boolean flags, actual timestamps or null, and an explicit empty/null value for unavailable evidence. Preserve uncertain capacity as occupied. Record accepted alias pairs with source evidence; do not silently rewrite history.

Research exceptions include the exact profile/query, attempts spent, last observed state and next action. `send_confirmation` records the trusted user request or direct evidence, confirmed contact IDs, known date/time precision and timezone. The latest `handed_off_at` plus `handed_off_ready` identifies the only batch eligible for the optional next-batch confirmation convention.

## Save and recover

1. **Own the write.** One coordinator owns the tracker and private state. Re-read actual headers/contact identities or local revision; stop on another writer, unexpected mapping or unresolved conflicting ownership. For local saves, hold a private OS file lock through the reread, journal and replacement; Python's standard-library `fcntl.flock` supplies it on the supported Mac host. External editors may ignore that lock, so resolve active user editing before replacement.
2. **Journal the change.** Save a `planned` write with exact affected identities, current values and intended values. Mark it `attempted` before the mutation. Preserve original status/date/reply fields unless the requested operation changes them.
3. **Apply narrowly.** Google mode updates only checked cells/ranges through the selected native tools. Local mode writes a complete validated next JSON file in the same private folder and atomically replaces the master only if its reread revision/content still matches. Increment its revision; preserve the before snapshot in the journal. Never overwrite concurrent user changes.
4. **Read back.** Compare affected values and preserved fields with the intended result. Only then mark the write `verified`, update the private batch and report saved. A successful tool return alone is insufficient.
5. **Recover uncertainty.** Failed/timed-out writes stay `reconciliation_required`. Read actual state and obtain authoritative proof that the original operation has failed, terminated or settled before any retry. Exact intended values support saved-state reconciliation; exact before values alone do not prove failure because the original write may still be in flight. Only settled failure plus unchanged before values permits a controlled retry. Partial/conflicting values require a new narrow plan preserving user edits once the earlier operation is settled. Never append another copy because a response was lost.

Match uncertain Google appends by stable Contact ID and canonical profile URL across the live table before attempting another append. Duplicate IDs or identity conflicts hold affected changes for review. If safe readback is unavailable, retain accepted findings privately as unsynced and continue independent work; do not claim the sheet is current.

Save `state.json` with the same single-writer, reread and atomic-replacement discipline. An interrupted batch keeps its reservations and evidence. Reconcile a saved tracker write before replaying a stale batch step; conversely, a recorded draft does not imply a tracker write succeeded. Never delete old batches, suppression or send history to make a fresh run appear empty.
