# Google Sheets write protocol

> **Required:** Python 3.10+, a bound Google tracker and native Drive/Sheets read/write tools.
> **Runs in:** Codex app; the central chat invokes the connector.
> **Computer use:** None.

Follow [operating rules](operations.md) and the backend-independent [queue and handoff contract](handoffs.md). Commands run from `Application Workflow/support/`; `--root` is the installation directory, never its `state/` child.

This guide covers discovery writes and the common authorize/readback/recovery steps. [Application tracking](tracking.md#save-to-google-sheets) prepares its own narrow change journal, then uses the same steps. Reports follow the separate [report guide](report.md). Local Excel uses [its own writer](local-excel.md).

## 1. Capture real native Sheets state

Follow the complete [snapshot capture procedure](native-evidence.md#assemble-a-google-sheets-snapshot) for metadata, native CellData, request masks and read coverage. Use it for the initial state, fresh authorization read and final readback.

**Before proceeding:** confirm the actual workbook identity, complete managed ranges and row-4 headers. Value-only responses are insufficient. Never label an unread range as empty or invent request coverage. The writer resolves named columns after a user reorder; it does not migrate an old workbook implicitly.

## 2. Prepare, refresh, authorize, then invoke the connector

1. `sheets.prepare(root, workbook_id, snapshot_or_path, owner)` acquires the persistent workbook claim and freezes the currently queued packets into a journal. A repeated call returns an unresolved journal. Another owner cannot take over based on its age.
2. Capture a fresh native snapshot immediately before mutation. `sheets.authorize_write(root, journal_id, fresh_snapshot)` checks every managed value against the saved prewrite state and rechecks packet/policy bindings. It writes `write_pending` **before** returning `spreadsheet_id`, `requests`, `journal_id`, a unique `attempt_id`, `attempt_recorded_at` and the `attempts` count. Retain this output privately with the response from that exact connector call.
3. Central sends those exact `requests` through Google Drive/Sheets `batch_update_spreadsheet` once, supplying `spreadsheet_id` and the tool's documented JSON serialization. The attempt fields belong to the local journal; do not add them to the Google request. The connector call is agent-mediated; this package contains no alternate Google authentication path.
4. Read the complete native managed state again and call `sheets.verify_and_commit(root, journal_id, readback_snapshot)`.

New source text uses literal `stringValue`; only generated HYPERLINK and managed summary formulas are formulas. Jobs dates are numeric dates in the profile timezone; original ISO source timestamps remain in Job Sources. New statuses are `New`; native date formats and status validation are applied. New links explicitly clear inherited formatting/rich-text links. Existing rows change only Last Seen and Seen Count; statuses, notes, referral contacts, First Seen and URLs stay intact. Updated source/coverage/rating metadata is separately managed; missing/incomplete coverage never closes a job.

Every append reserves new rows with native `insertDimension` before populating them, so a human row added at the previously observed edge shifts down and is preserved. First-data-row inserts inherit from the following blank data row, avoiding header styling. [Google's InsertDimensionRequest reference](https://developers.google.com/workspace/sheets/api/reference/rest/v4/spreadsheets/request#InsertDimensionRequest) defines this operation. After all insertions, the batch restores Daily Summary's eight open-ended formulas beginning at row 5: Google may otherwise shift a formula's first-row reference when rows are inserted there. Exact summary formula readback is required for commitment.

Every distinct source observation contributes once. Older observations never regress Last Seen or rewrite a previously saved First Seen. For a role first introduced by multiple packets in the same batch, First Seen is the earliest accepted observation across them. Job Sources keeps source policy/tier/rating/link provenance; cross-source overlap occupies one Jobs row. An accepted Blind stretch is not rescreened under the main policy.

Verification checks all managed values, preserved manual fields and every occupied Job Link: formula target, effective clickable destination, explicit formatting links and rich-text links must agree. Existing URLs must also match prior private accepted receipts. Explicit adoption of an existing workbook requires `state/writer/baseline-links.json` with `workbook_id` and `rows: [{job_key,url,evidence_url,verified_at}]` from independently verified per-job sources. Do not build it from the potentially damaged live link column. A changed role URL needs a separately reviewed repair, not an implicit overwrite.

Only successful readback installs a private saved receipt and moves packets from pending to done. Receipt-first installation is recoverable if a process exits during queue moves. Snapshot ingestion and report delivery frontiers are separate. A packet written to disk, a successful tool response or an attempted request never proves a saved row.

## 3. Reconcile uncertain outcomes

**After a timeout or interruption, do not send the batch again or release its packets.** Keep the journal/owner claim, capture fresh native state and follow [uncertain Google Sheets write recovery](upgrade-and-recovery.md#uncertain-google-sheets-write). That is the authoritative reconciliation and settlement procedure.

An exact after-state can commit without another write. An unchanged before-state still needs settlement for the current attempt; a mixed state needs reviewed repair. No automatic claim expiry or forced takeover is available. For edits before any attempt, use the recovery guide's [unattempted plan procedure](upgrade-and-recovery.md#unattempted-google-sheets-plan).

The Google connector does not expose a transaction spanning the prewrite read and write. Concurrent human appends are preserved by inserted rows, and readback detects unexpected additions. Human edits to an existing cell that this batch also updates can still race the final request: a last-moment edit to Last Seen or Seen Count can be overwritten. No compare-and-swap guarantee is claimed. This local claim coordinates one installation only; two independent installations must not write the same tracker.

## Verify

Run the [offline checks](verification.md), then a scoped pilot on the user's selected tracker. Native-shaped fixtures exercise request generation and readback checks; they cannot certify live connector behavior.
