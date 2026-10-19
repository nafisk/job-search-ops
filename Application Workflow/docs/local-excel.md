# Local Excel tracker

> **Required when selected:** Python 3.10+, a private `.xlsx` path and Codex's app-provided Node/spreadsheet runtime. See [runtime setup](tools.md#checks-and-maintenance).
> **Runs in:** Codex app with local file access; Google Sheets and the Excel desktop app are not required.
> **Computer use:** None for workbook writes. Keep the file closed in other apps during a write.

Choose `tracker.provider: "local_xlsx"` during [onboarding](../ONBOARDING.md) and set an absolute, private `.xlsx` path. Main, its selected helpers and Blind use this one workbook. Google Drive and Google Sheets are not required. Gmail and Calendar are required only when their corresponding features are selected.

The local writer uses Python's standard library for the queue and file checks, and Codex's bundled `@oai/artifact-tool` for Excel import, editing and export. It does not install Python or Node packages. The assistant loads the Spreadsheets skill, calls `load_workspace_dependencies`, and uses the returned Node executable and Node packages directory. Follow that skill's artifact-operation marker before the first creation/edit command.

The bundled artifact runtime cannot calculate `HYPERLINK`, and its documented API does not expose native hyperlinks or column hiding. A narrow post-export fallback adds the actual Jobs hyperlink relationships and the hidden Job Key column. It also corrects the runtime's numeric date caches for exact constant-text formulas; those formulas remain unchanged. Other ZIP parts and worksheet cells are preserved. Excel uses these [native hyperlink relationships](https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.spreadsheet.hyperlink) and [column visibility attributes](https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.spreadsheet.column). The result is reopened with artifact-tool without another export, then inspected independently; no Google response is fabricated.

## Create and use the workbook

Run these commands from `Application Workflow/support`, substituting the real paths returned by Codex. Keep runtime paths in the private installation, never in the shared repository.

```sh
python3 -m job_search_ops local-init --config /absolute/private/config.json --node /absolute/bundled/node --node-modules /absolute/bundled/node_modules
python3 -m job_search_ops local-sync --config /absolute/private/config.json --node /absolute/bundled/node --node-modules /absolute/bundled/node_modules
```

`local-init` creates the tracker from the supplied blank template and records its actual saved-file readback. It refuses to replace an existing unrecognized file. This first version supports this template and its ordinary cell edits; importing arbitrary workbooks, macros, external workbook links, embedded objects, charts, pivots and protected sheets requires a separate migration.

Producers enqueue discoveries as usual. Only the coordinator runs `local-sync`. The existing stable Job Key and source-event rules prevent duplicate jobs and duplicate sightings, preserve manual status/contact/notes, and retain each source's screening policy. Blind uses the same Jobs tab, with its company and coverage data in the same file.

**Close the workbook before a scheduled run or sync.** Use one writing host, and do not edit the file simultaneously through another app or a synced copy. The writer checks Excel/LibreOffice lock files and the entire original file's hash. Its lock protects this package's writers; it cannot lock out every external editor.

## Apply reviewed tracking changes

Tracking-only configurations can update existing rows or record an actual application without running discovery. The coordinator first reads the actual workbook and checks the selected application/interview sources. It saves a private plan:

```json
{
  "workbook_id": "local:your-installation-id",
  "expected_file_sha256": "actual-sha256-of-the-reviewed-xlsx",
  "updates": [{
    "job_key": "example:req-1",
    "field": "Application Status",
    "old_value": "Applied",
    "new_value": "Interviewing",
    "evidence_ref": "private run manifest and exact reviewed message reference"
  }]
}
```

```sh
python3 -m job_search_ops local-update --config /absolute/private/config.json --plan /absolute/private/tracking-plan.json --node /absolute/bundled/node --node-modules /absolute/bundled/node_modules
```

Only Application Status, Notes and Referral Contact are accepted. Every change needs the expected old value and an evidence reference. A changed file or old value stops the update; review fresh evidence before making a new plan. The file adapter does not infer status or contact anyone. Committed tracking receipts join the shared receipt checkpoint automatically. The [report](report.md) freezes them alongside discovery receipts, including recovery of older committed local tracking journals. Delivery acknowledges only that frozen set.

When a confirmed application is absent from the tracker, use `updates: []` and add `new_records` to the same plan:

```json
"new_records": [{
  "job_key": "example:req-1",
  "company": "Example Company",
  "title": "Software Engineer",
  "url": "https://careers.example.com/jobs/req-1",
  "status": "Applied",
  "observed_at": "2026-10-19T09:00:00-04:00",
  "evidence_ref": "private manifest: exact application confirmation",
  "role_evidence_ref": "private manifest: independently verified official role page"
}]
```

New records require both application evidence and a verified role identity/link; the allowed statuses are Applied, Interviewing, Rejected and Closed. They are labeled **Tracking evidence** with `not_screened` provenance. They are not qualified discovery recommendations. Duplicate keys or role URLs are rejected, and later discovery of the same role merges into that row. Keep unmatched email facts in the private run record and brief until the role identity can be verified.

## Save proof and recovery

The writer exports a sibling candidate file, reopens it with artifact-tool, and independently reads the actual OOXML. It compares planned values, role-specific links, all other cell contents, untouched cell formatting, frozen panes, merged cells and column widths/visibility. It keeps a backup, checks the original file again, atomically replaces it, and verifies the final bytes before recording success. Literal text beginning with `=` stays literal text. ISO-looking evidence text uses constant-text formulas to prevent automatic date conversion; the exact original text and saved formula result are both checked. Ordinary job dates remain numeric Excel dates.

If publication succeeded but receipt installation failed, rerun the same command (and the same tracking plan, for `local-update`). Recovery recognizes the actual published file hash and records the receipt without repeating the edit. This readback-only recovery remains available during a pending preference pilot; retrying an unpublished edit still requires the explicit manual pilot described in [preferences](preferences.md). If another edit occurred, the writer stops for reconciliation. Keep the private installation, candidate files, hidden sibling backups and journals until recovery is complete. Never delete a journal to force a retry.

Saved-file verification proves the contents of the `.xlsx` file. It is not a claim that a person opened the workbook in Excel. Source completeness, saved jobs and delivered briefs remain separate checks.
