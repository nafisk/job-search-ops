# Discovery export

The [export template](../sheets/discovery-export.xlsx) lists saved jobs in three tabs for LinkedIn Alerts, Blind Research and Referral Portals. Each starts with Targets. Set **Application status** by hand to **Not applied**, **Applied** or **On hold**. The main tracker records application and interview evidence.

## Set up a destination

Confirm the export destination for the user's saved discovery history. Use their private `config.json`.

- **Local Excel.** Reuse the confirmed export file or copy the template to a durable private path. Check the tabs and headers with the [Excel writer runtime](local-excel.md#create-and-use-the-workbook).
- **Google Sheets.** Use the confirmed Drive account and folder. Reuse the export or import the template as a native Sheet. Verify the ID and headers. Restore missing table, date, or dropdown settings. Write, read back, and clear a blank test cell. Confirm it is blank again. Reconcile uncertain imports before retrying.

Add confirmed searches, portal links, and fallback clicks to Targets. For an older export with matching posting headers, add Application status as the last column of each posting table and give it the three dropdown choices above. Record the path or URL in the private setup summary. Export only the template fields.

Run from `Application Discovery/support/`:

```sh
python3 -m job_search_ops discovery-export-select --config /absolute/private/config.json \
  --destination local_xlsx --local-path /absolute/private/discovery-results.xlsx

python3 -m job_search_ops discovery-export-select --config /absolute/private/config.json \
  --destination google_sheets --spreadsheet-id VERIFIED_ID --google-identity VERIFIED_ACCOUNT
```

## Switch the next export

Say **“Set my next discovery export to Google Sheets”** or **“Set my next discovery export to Local Excel.”** Recheck the destination and Targets. Omit the binding arguments to reuse a saved path or ID. Exports start off. Use `--destination off` to pause. Manual statuses belong to the selected workbook and source tab.

## Export saved postings

In the main chat, run this after the tracker save or on an export-only request:

```sh
python3 -m job_search_ops discovery-export-plan --config /absolute/private/config.json \
  --output /absolute/private/discovery-export-plan.json
```

Use the central run’s `--pilot-update-id` for an authorized replacement pilot. Skip `off`. Otherwise, write the plan’s `tabs`. Found on uses the first accepted date per source in the installation timezone, stored as a spreadsheet date serial.

1. Read the bound file, or verify the Google account and IDs and read the bound Sheet. Find posting tables by their headers. Match generated fields to the last verified export by posting URL so sorting is safe. On first use, expect blank rows or an exact match to the plan. Reconcile unexpected changes. Save current posting rows as a JSON object keyed by the three tab names, with each value an array of rows in column order. Include the status column and use null for empty cells. If an older Referral Portals tab has a Referral hold column, leave its existing cells alone and omit that column from the rows supplied to the merge.
2. Preserve statuses before writing. The merge keeps a status with its verified posting URL or accepted alias. New rows use Not applied.

```sh
python3 -m job_search_ops discovery-export-merge-status \
  --plan /absolute/private/discovery-export-plan.json \
  --current /absolute/private/current-posting-rows.json \
  --output /absolute/private/discovery-export-write.json
```

3. Save the merged plan as the write intent. Recheck current rows just before writing. Update the posting fields by header and extend dates and dropdowns as needed. For Excel, verify a sibling copy before replacing the unchanged original. For Google, batch typed `updateCells` writes and use `updateTable` to extend bounds. Keep the workbook idle during the write.
4. Match saved headers and rows to the merged plan. Record the verified result privately and return its path or URL. Reconcile uncertain writes before retrying. Report failures and coverage gaps.
