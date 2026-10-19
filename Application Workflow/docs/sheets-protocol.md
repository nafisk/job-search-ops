# Google Sheets write protocol

> **Required:** Python 3.10+, a bound Google tracker and native Drive/Sheets read/write tools.
> **Runs in:** Codex app; the central chat invokes the connector.
> **Computer use:** None.

Follow [operating rules](operations.md) and the backend-independent [queue and handoff contract](handoffs.md). Commands run from `Application Workflow/support/`; `--root` is the installation directory, never its `state/` child.

This guide covers discovery writes and the common authorize/readback/recovery steps. [Application tracking](tracking.md#save-to-google-sheets) prepares its own narrow change journal, then uses the same steps. Reports follow the separate [report guide](report.md). Local Excel uses [its own writer](local-excel.md).

## 1. Capture real native Sheets state

Read metadata to resolve current sheet IDs and grid row counts. Read native CellData for all managed columns from row 4 through the last allocated row of **Jobs**, **Job Sources**, **Rated Companies**, and **Rated Search Coverage**, plus **Daily Summary A4:B12**. Divide large reads into contiguous bounded chunks. Retain the original responses and request ranges; omitted trailing empty CellData is normal.

Request this cell field mask:

```text
userEnteredValue,effectiveValue,hyperlink,userEnteredFormat(textFormat),effectiveFormat(textFormat),textFormatRuns
```

Use `sheets.combine_snapshot(metadata, cell_responses, read_ranges, cell_fields)` or the CLI snapshot assembler. It accepts actual native connector responses, including `structuredContent` wrappers. The resulting native JSON carries `_read_ranges` and `_cell_fields`, recording what was actually requested. These fields must not be invented to cover unread cells. A value-only range response is insufficient. Every required header must be present once on row 4. Header names and sheet IDs, not remembered numeric IDs, control writes.

The seven-tab schema is `Application Workflow/sheets/workbook-schema.json`. Jobs keeps the original fourteen columns and a hidden managed **Job Key** column; the initializer places it in O. The writer resolves the named column after a user reorder. It does not migrate an old workbook implicitly.

## 2. Prepare, refresh, authorize, then invoke the connector

1. `sheets.prepare(root, workbook_id, snapshot_or_path, owner)` acquires the persistent workbook claim and freezes the currently queued packets into a journal. A repeated call returns an unresolved journal. Another owner cannot take over based on its age.
2. Capture a fresh native snapshot immediately before mutation. `sheets.authorize_write(root, journal_id, fresh_snapshot)` checks every managed value against the saved prewrite state and rechecks packet/policy bindings. It writes `write_pending` **before** returning `{spreadsheet_id, requests, journal_id}`.
3. Central sends those exact `requests` through Google Drive/Sheets `batch_update_spreadsheet` once, supplying `spreadsheet_id` and the tool's documented JSON serialization. The connector call is agent-mediated; this package contains no alternate Google authentication path.
4. Read the complete native managed state again and call `sheets.verify_and_commit(root, journal_id, readback_snapshot)`.

New source text uses literal `stringValue`; only generated HYPERLINK and managed summary formulas are formulas. Jobs dates are numeric dates in the profile timezone; original ISO source timestamps remain in Job Sources. New statuses are `New`; native date formats and status validation are applied. New links explicitly clear inherited formatting/rich-text links. Existing rows change only Last Seen and Seen Count; statuses, notes, referral contacts, First Seen and URLs stay intact. Updated source/coverage/rating metadata is separately managed; missing/incomplete coverage never closes a job.

Every append reserves new rows with native `insertDimension` before populating them, so a human row added at the previously observed edge shifts down and is preserved. First-data-row inserts inherit from the following blank data row, avoiding header styling. [Google's InsertDimensionRequest reference](https://developers.google.com/workspace/sheets/api/reference/rest/v4/spreadsheets/request#InsertDimensionRequest) defines this operation. After all insertions, the batch restores Daily Summary's eight open-ended formulas beginning at row 5: Google may otherwise shift a formula's first-row reference when rows are inserted there. Exact summary formula readback is required for commitment.

Every distinct source observation contributes once. Older observations never regress Last Seen or rewrite a previously saved First Seen. For a role first introduced by multiple packets in the same batch, First Seen is the earliest accepted observation across them. Job Sources keeps source policy/tier/rating/link provenance; cross-source overlap occupies one Jobs row. An accepted Blind stretch is not rescreened under the main policy.

Verification checks all managed values, preserved manual fields and every occupied Job Link: formula target, effective clickable destination, explicit formatting links and rich-text links must agree. Existing URLs must also match prior private accepted receipts. Explicit adoption of an existing workbook requires `state/writer/baseline-links.json` with `workbook_id` and `rows: [{job_key,url,evidence_url,verified_at}]` from independently verified per-job sources. Do not build it from the potentially damaged live link column. A changed role URL needs a separately reviewed repair, not an implicit overwrite.

Only successful readback installs a private saved receipt and moves packets from pending to done. Receipt-first installation is recoverable if a process exits during queue moves. Snapshot ingestion and report delivery frontiers are separate. A packet written to disk, a successful tool response or an attempted request never proves a saved row.

## 3. Reconcile uncertain outcomes

After a timeout or interruption, do not call the connector again. Read actual native state and call `sheets.reconcile(root, journal_id, snapshot)`:

- Exact planned state: verify and commit the existing write, with no second mutation.
- Exact before-state: mark `awaiting_settlement`; an unchanged snapshot cannot prove that a timed-out call will not land later. No automatic retry is allowed. A changed grid size is a conflict even if the visible cells are unchanged, because blank inserted rows do not prove ownership.
- Mixed or user-edited state: preserve a conflict and queue; no automatic replay. Investigate the narrow cells using the before/after journal. Only after an explicit reviewed repair restores a verifiable before or after state can reconciliation proceed.

Retrying an unchanged state requires `sheets.reconcile(root, journal_id, snapshot, settlement)` (CLI `reconcile --settlement file.json`). Evidence must bind `journal_id` and a timezone-qualified `verified_at`. Use `kind: native_terminal_failure` plus the actual `response` containing a terminal native error code (400, 401, 403, 404, 409, 412 or 422), or `kind: human_reconciled` plus a genuine `human_turn_ref` and the explicit confirmation `The previous connector operation has ended; no pending call can still apply this batch.` Generic tool errors, timeouts and 5xx responses do not prove settlement. Once marked `retryable`, capture another fresh snapshot and authorize once. Never manufacture human confirmation.

If a user edits or sorts before the first write, `sheets.cancel_unattempted(root, journal_id, owner)` permits a fresh plan. It cannot cancel an attempted or uncertain mutation. `queue.release_claim(root, workbook_id, owner)` requires the recorded owner and no unresolved journals. There is no automatic claim expiry or force-takeover API.

The Google connector does not expose a transaction spanning the prewrite read and write. Concurrent human appends are preserved by inserted rows, and readback detects unexpected additions. Human edits to an existing cell that this batch also updates can still race the final request: a last-moment edit to Last Seen or Seen Count can be overwritten. No compare-and-swap guarantee is claimed. This local claim coordinates one installation only; two independent installations must not write the same tracker.

## Verify

Run the [offline checks](verification.md), then a scoped pilot on the user's selected tracker. Native-shaped fixtures exercise request generation and readback checks; they cannot certify live connector behavior.
