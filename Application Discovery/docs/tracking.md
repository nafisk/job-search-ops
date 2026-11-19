# Application and interview tracking

Run the [`main` execution check](operations.md#routine-operation) before any read. Load the selected tracking sources. Email-alert discovery and Gmail tracking have separate settings.

1. **Read the selected scope.** Freeze the window and overlap, including unresolved older items. Verify account identity. Use fully paginated native reads for selected Gmail receipts, correspondence and Sent history, selected calendars, or the exact [Messages conversation](messages.md). Keep mail and calendar state intact. Report access gaps.
2. **Bind evidence to the exact application.** Use the full message or event, employer, requisition and process. Keep submission, replies, rejection, response owed, stage, invitation, booking, RSVP, attendance and outcome as separate facts. Require affirmative evidence for each. Keep employer deadlines separate from suggested follow-ups. Carry ambiguous facts forward as unresolved. Use the [application](../support/toolkit/APPLICATIONS.md), [lifecycle](../support/toolkit/LIFECYCLE.md), [interview](../support/toolkit/INTERVIEWS.md) and [coverage](../support/toolkit/COVERAGE.md) contracts.
3. **Handle saved Messages text.** Require verified conversation attribution and preserve speaker, negation and uncertainty. Follow the [saved transcript rules](messages.md#saved-voice-message-text) for absent text, unsupported tools and read failures.
4. **Save supported changes.** Central writes evidence-backed updates through the selected backend. Compare current manual fields before writing and preserve First Seen and stronger user edits. For a confirmed application absent from the tracker, add a tracking record only after verifying the exact official role and application evidence. Keep unbound facts in the private run record.
5. **Report.** Include company, role, stage or status, date or unknown, next action and gaps. Keep raw evidence and identifiers private. Track source coverage independently from accepted facts and report delivery.

Application opening, recruiting, sending and calendar actions require their own requests.

## Save to Google Sheets

Commands run from `Application Discovery/support/`. `--root` is the installation directory containing `installation.json`, never its `state/` child. Use the complete native snapshot described in [snapshot capture](native-evidence.md#assemble-a-google-sheets-snapshot).

1. Capture the real tracker and inspect exact identities and current manual fields:

```sh
python3 -m job_search_ops tracking-review --workbook WORKBOOK_ID --snapshot /absolute/private/tracking-before.json --output /absolute/private/tracking-review.json
```

2. Build a private plan from that result and independently reviewed source evidence:

```json
{
  "workbook_id": "actual-bound-workbook-id",
  "expected_state_sha256": "actual-digest-returned-by-tracking-review",
  "updates": [{
    "job_key": "example:req-1",
    "field": "Application Status",
    "old_value": "Applied",
    "new_value": "Interviewing",
    "evidence_ref": "private manifest: exact reviewed employer message"
  }]
}
```

Allowed fields are Application Status, Notes and Referral Contact. An expected-old-value mismatch stops the plan. Existing role links must match accepted receipts or an independently reviewed adoption baseline.

Before deciding an application is new, read its accepted identity history:

```sh
python3 -m job_search_ops role-state --root /absolute/private --workbook WORKBOOK_ID
```

This private result maps alternate IDs and URLs to the saved canonical Job Key. Both tracking writers check that history. A `new_records` entry matching either accepted alias is rejected with its canonical key; use that key and fresh reviewed old values in `updates`. Alias-key updates also return canonical guidance. Conflicting key/URL mappings require identity reconciliation. The writer does not silently convert an addition into an update or replace the canonical link, status, Notes or Referral Contact.

Only for a confirmed application absent from this history and the tracker, use the same `new_records` shape shown in [local tracking](local-excel.md#apply-reviewed-tracking-changes); keep `expected_state_sha256` for Google. New rows are marked **Tracking evidence**, with discovery screening not evaluated.

3. Prepare the journal. The command reads the installed `config.json`, requires at
least one selected tracking source, and checks that Google Sheets and this exact
verified workbook are bound. A disabled tracking selection cannot create a journal:

```sh
python3 -m job_search_ops tracking-prepare --root /absolute/private --workbook WORKBOOK_ID --snapshot /absolute/private/tracking-before.json --plan /absolute/private/tracking-plan.json
```

4. [Apply the prepared batch](sheets-protocol.md#apply-a-prepared-batch). Use the same native snapshot, authorization, write, and readback steps as discovery. For an uncertain write, follow the [recovery procedure](upgrade-and-recovery.md#uncertain-google-sheets-write).

## Save to Excel and report

Use [local-update](local-excel.md#apply-reviewed-tracking-changes), binding the reviewed file hash and exact old values. Both backends’ receipts enter the same [report checkpoint](report.md). Set the public snapshot’s `tracking_updates` to the prepared brief’s exact `tracking_summary`; render every identity and safe change label. A late tracking receipt waits for the next brief. Private evidence stays in the save journal, not the report body.
