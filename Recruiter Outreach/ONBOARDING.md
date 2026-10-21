# Set up recruiter outreach

> **Required:** Codex desktop on macOS, local file access, Python 3.10+ for private JSON records, a supported browser and your LinkedIn account. Google Drive/Sheets access is required only for the Google tracker.
> **Runs in:** Codex app. This module does not require an Application Workflow installation.
> **Computer use:** Required for live LinkedIn profiles and unsent draft preparation. You log in and perform final sends.

Give the agent this guide and ask: **“Set up Recruiter Outreach with me.”** Setup creates private settings and an empty tracker; it does not research people, draft messages or start a schedule.

## 1. Choose your workspace and tracker

Choose a permanent private folder outside this repository and any shared export folder. Check its actual filesystem location, including symlinks and case aliases, before saving. Set owner-only permissions: `0700` on private folders and `0600` on private files, including journals, drafts and temporary replacements. Keep one installation per person; never point a new installation at someone else's contacts or batches.

Choose **local JSON** for the smallest setup, or **Google Sheets** for a visible cloud tracker. Both keep draft reservations and recovery records in private local JSON. Follow [tracker setup](tracker.md#set-up-storage) to create and read back the selected storage. Python's standard library is sufficient; no extra package is needed. CSV is an optional local view, not a second master.

An existing recruiter tracker may be adopted only after reviewing its actual headers, contact identities, statuses and unresolved drafts. Map fields explicitly and preserve history. Do not import personal source files from this repository's author, replace an existing workbook or use the seven-tab jobs tracker as a recruiter table.

## 2. Connect only the selected tools

| Capability | Setup and proof |
| --- | --- |
| Codex and local files | Open the permanent checkout in the [Codex app](https://developers.openai.com/codex/app/). Confirm Python 3.10+ is available and a private JSON file can be saved and read back. [Install Python](https://www.python.org/downloads/) only if missing. |
| Supported browser | Follow the [browser connection guide](https://learn.chatgpt.com/docs/chrome-extension). Select Chrome or another browser the current host supports. Log into LinkedIn yourself; verify the observed account matches your chosen identity. Preserve unrelated tabs. |
| Google tracker, if selected | Connect the [Google tools](https://learn.chatgpt.com/docs/plugins). Read the installed Google Sheets skill before Google access/effects. Verify account identity, access to the exact workbook, metadata/cell reads and narrow writes with readback. Follow the current tool schemas. |
| Research | Use available public search/page reads and the supported LinkedIn browser. Search results find leads; live profiles supply current evidence. |

The [shared tool reference](../Application%20Workflow/docs/tools.md) explains connector and browser boundaries. Its Gmail, Calendar, Messages and scheduling requirements belong to their selected application features; they are not requirements here. Do not install a CLI, email-finder service, extra MCP server or alternate credential flow for this setup.

If a selected capability is unavailable, record the missing step. Do not mark setup ready or substitute another account. A connection establishes access, not permission to send.

## 3. Save your choices and approved copy

Create private `settings.json` using this starting shape. Replace nulls and empty targets through the conversation; they are deliberately incomplete values. Save the absolute private folder and repository locations in the configured chat's instructions.

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

Choose your IANA timezone, account identity and desired candidate specialties/levels. The research count is a configurable goal, not proof of full coverage or a draft quota. Set a positive outstanding-draft ceiling and a pilot count no larger than it. Google mode sets `backend` to `google_sheets` and requires the actual workbook ID and expected account.

Default to qualified contacts and explicit send confirmation. Two optional preferences reproduce more permissive review habits:

- **Review drafts for uncertain contacts:** if enabled, preserve Needs review/employer holds and label their drafts for review. Exclusions, opt-outs and prior outreach still block new drafts.
- **“Next batch” confirms sends:** if enabled after explicit discussion, that phrase confirms only the immediately preceding handed-off ready batch. It never confirms blocked contacts or unrelated older drafts. The agent records that request as the confirmation source.

Approve your own copy before any drafting. Use this neutral starting point, replacing every fact placeholder with something you can support:

```text
Subject: [Target role] opportunities at [Company]

Hi [First name],

I'm exploring [target roles] and wanted to ask whether you recruit for that area at [Company].

My background includes [one or two verified, relevant achievements].

I'd be glad to share more if that fits the teams you support.

Best,
[Your name]
```

Prepare a shorter approved connection note if that channel is selected. At runtime only the approved recipient/company substitutions may change automatically. Never copy another person's achievements, invent an application, claim a resume is attached or silently truncate copy to fit.

## 4. Check setup, then request a pilot

1. Read back private settings and empty storage; confirm identity, destination, required fields and no unresolved migration/write issues.
2. Confirm approved copy has no fact placeholders. Mark `setup_status` as `ready` only after selected tool/storage checks pass; retain dated proof privately.
3. Request [research](research.md) for one named company or supply an explicit contact roster for the same verification process.
4. Review the roster, then separately request up to two [unsent drafts](run.md). Verify both remain accessible before a larger batch.
5. Review, attach your resume where supported and send personally. Confirm the sends to update the tracker.

Tool setup alone never proves draft persistence or sending. If the pilot is blocked, keep its actual state and next action; no recurring automation is created.

## Change preferences

Ask the configured chat to change the named private setting. Preserve contacts, suppression, copy history, draft text and reservations. New copy needs approval; changing account, tracker or browser requires fresh identity/storage checks before use. Reducing capacity stops new allocation until existing occupied slots fit. Enabling either optional convention is explicit opt-in, never inferred from installing these guides.
