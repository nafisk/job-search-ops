# Application and interview tracking

> **Required when selected:** At least one authorized read source—Gmail, Google Calendar or [Mac Messages MCP](messages.md)—plus Python 3.10+ and the configured tracker. Connect only the sources selected.
> **Runs in:** Codex app through native connectors/MCP; the central chat saves supported changes.
> **Computer use:** None for routine tracking; initial account/OS access may need your participation.

Use [applications](../support/toolkit/APPLICATIONS.md), [lifecycle](../support/toolkit/LIFECYCLE.md), [interviews](../support/toolkit/INTERVIEWS.md) and [coverage](../support/toolkit/COVERAGE.md) as pure acceptance helpers. Their inputs must come from independently inspected native evidence. Read saved source choices first. Gmail tracking, Calendar and Apple Messages are independent: run only the selected sources, and skip this phase when none are selected. Email-alert discovery does not enable Gmail tracking. Unselected sources are not configured; missing selected sources retain visible gaps.

1. Freeze the configured tracking window, overlap and older unresolved items. Verify account identities before private reads. Only if `tracking.gmail` is enabled, read Gmail application receipts, employer/recruiter correspondence and Sent evidence in bounded, fully paginated queries. Do not change mail labels, read state or messages. Calendar-only or Messages-only tracking requires no Gmail access.
2. Bind each event to exact employer and role/requisition/process using the full message and existing accepted identities. Ambiguous association stays unresolved. A tracker Applied label, browser tab disappearance or prepared form does not create a confirmed submission.
3. Keep submission, rejection, response obligation, interview stage, invitation, booking, RSVP, attendance and outcome as separate facts. A calendar event is not proof of attendance; positive self-assessment is not advancement. Preserve genuine employer deadlines separately from suggested follow-ups.
4. If Calendar is enabled, enumerate configured calendars/date bounds through native read tools. Do not book or RSVP. If Messages is enabled, use the explicitly configured exact conversation and [optional Messages connection](messages.md); never scan all conversations as a fallback.
5. Only when the selected MCP exposes saved voice transcripts with verified conversation attribution, read existing Apple text; mark this source unavailable otherwise. Do not retrieve/play/upload audio or generate transcripts. Confirmed absent saved text is a visible nonblocking skip. Read failures remain gaps. Quote claims privately, preserve uncertainty/negation/speaker and match exact role/process with adjacent context. No inferred facts from an unbound recording.
6. Use the save procedure below. Propose only narrow, evidence-supported status changes; reconcile manual edits before accepting. The central coordinator alone writes authorized fields through the selected [local Excel](local-excel.md) or [Google Sheets](sheets-protocol.md) path, using fresh-read/journal/readback discipline. For an application missing from either tracker, its tracking writer can add a reviewed record with exact official role identity and application evidence. Label it tracking evidence, with discovery screening not evaluated; do not invent a qualifying discovery packet. Unbound facts stay in the private run record and report. Never overwrite First Seen, Notes or a manual status based on weaker evidence. An uncertain write remains unaccepted.
7. Produce a safe report projection: company/role, stage/status, actual date or unknown, next action and concise uncertainty. Keep contact handles, conversation IDs, raw correspondence/transcripts and evidence paths private. Ingestion checkpoints, accepted facts and delivered report baselines remain separate.

A completed tracking pass can include disclosed source exceptions. This does not authorize application opening, recruiter research, drafting, sending, booking or invitations.

Before reading sources, run the [execution check](operations.md) for `main`.
Pending preference changes require their explicitly requested replacement pilot.

## Save to Google Sheets

Commands run from `Application Workflow/support/`. `--root` is the installation directory containing `installation.json`, never its `state/` child. Use the complete native snapshot described in [snapshot capture](native-evidence.md#assemble-a-google-sheets-snapshot).

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

4. Capture fresh native state. Run `authorize-write --root /absolute/private --journal JOURNAL_ID --snapshot /absolute/private/tracking-fresh.json`, send its exact batch once using native Sheets tools, then obtain complete readback and run `commit --root /absolute/private --journal JOURNAL_ID --snapshot /absolute/private/tracking-after.json`. These are `python3 -m job_search_ops` commands. Keep the tracker idle during the write: Google provides no conditional cell transaction protecting a simultaneous human edit to the same field.
5. After a timeout, follow [uncertain-write recovery](upgrade-and-recovery.md#uncertain-google-sheets-write); do not send the batch again. Only exact verified saved state creates a tracking receipt.

## Save to Excel and report

Use [local-update](local-excel.md#apply-reviewed-tracking-changes), binding the reviewed file hash and exact old values. Both backends’ receipts enter the same [report checkpoint](report.md). Set the public snapshot’s `tracking_updates` to the prepared brief’s exact `tracking_summary`; render every identity and safe change label. A late tracking receipt waits for the next brief. Private evidence stays in the save journal, not the report body.
