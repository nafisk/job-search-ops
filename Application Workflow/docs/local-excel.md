# Local Excel tracker

> **Required when selected:** Python 3.10+, a private `.xlsx` path and Node and `@oai/artifact-tool`. See [runtime setup](tools.md#checks-and-maintenance).
> **Computer use:** None for workbook writes. Keep the file closed in other apps during a write.

Choose `tracker.provider: "local_xlsx"` during [onboarding](../ONBOARDING.md) and set an absolute, private `.xlsx` path. Main, its selected helpers and Blind use this one workbook. Google Drive and Google Sheets are not required. Gmail and Calendar are required only when their corresponding features are selected.

Verify the absolute paths to the supported Node executable and the `node_modules` directory containing `@oai/artifact-tool`. Pass both to the writer. Python manages queue and file checks. `@oai/artifact-tool` imports, edits and exports the workbook.

The artifact runtime lacks native links, column hiding and `HYPERLINK` calculation. After export, the bridge adds Jobs link relationships, hides Job Key and corrects numeric date caches for exact constant-text formulas. It preserves formulas, other cells and ZIP parts. Reopen with artifact-tool without exporting again, then inspect the file independently. See the Excel [hyperlink](https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.spreadsheet.hyperlink) and [column visibility](https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.spreadsheet.column) fields.

## Create and use the workbook

Run these commands from `Application Workflow/support`, substituting the verified runtime paths. Keep runtime paths in the private installation, never in the shared repository.

```sh
python3 -m job_search_ops local-init --config /absolute/private/config.json --node /absolute/runtime/node --node-modules /absolute/runtime/node_modules
python3 -m job_search_ops local-sync --config /absolute/private/config.json --node /absolute/runtime/node --node-modules /absolute/runtime/node_modules
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
python3 -m job_search_ops local-update --config /absolute/private/config.json --plan /absolute/private/tracking-plan.json --node /absolute/runtime/node --node-modules /absolute/runtime/node_modules
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

New records require both application evidence and a verified role identity/link; the allowed statuses are Applied, Interviewing, Rejected and Closed. They are labeled **Tracking evidence** with `not_screened` provenance. They are not qualified discovery recommendations.

Read the private accepted aliases using [role-state](tracking.md#save-to-google-sheets), substituting the local workbook ID. A duplicate key, URL or previously accepted alternate ID/URL is rejected before changing the workbook. Use the returned canonical Job Key and fresh expected old values to update the existing row; the original role link and unrelated manual fields stay intact. Conflicting identities require reconciliation. Later discovery merges into the accepted row. Keep unmatched email facts in the private run record and brief until the role identity can be verified.

## Save proof and recovery

The writer exports a sibling candidate file, reopens it with artifact-tool, and independently reads the actual OOXML. It compares planned values, role-specific links, all other cell contents, untouched cell formatting, frozen panes, merged cells and column widths/visibility. It keeps a backup, checks the original file again, atomically replaces it, and verifies the final bytes before recording success. Literal text beginning with `=` stays literal text. ISO-looking evidence text uses constant-text formulas to prevent automatic date conversion; the exact original text and saved formula result are both checked. Ordinary job dates remain numeric Excel dates.

For an interrupted save or receipt, follow [local Excel recovery](upgrade-and-recovery.md#uncertain-local-excel-write).

Saved-file verification proves the contents of the `.xlsx` file. It is not a claim that a person opened the workbook in Excel. Source completeness, saved jobs and delivered briefs remain separate checks.
