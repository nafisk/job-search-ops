# Upgrade and recovery

> **Required:** The existing private state, journals and resource bindings, Python 3.10+, and access to the selected tracker/report destination.
> **Runs in:** Codex app with the same tools and identities used by that installation.
> **Computer use:** Only if recovering a selected browser task; never replace missing connector access with browser account access.

Local helper commands in this guide run from `Application Workflow/support/` in the permanent checkout.

Preserve the checkout, private state, resource bindings and selected tracker as separate assets. Back up private state privately; never use the public repository as a personal-data backup. No cleanup of dated sessions authorizes deleting durable job state.

## Interrupted setup

Read the resource journal before recreating anything. If a workbook/chat/schedule creation outcome is unknown, inspect only the selected resource: a local file and its journal, or the configured connected account/project. Match the intent, actual IDs and observed content; do not guess an ID or create a replacement to make setup proceed. Record the verified resource and resume the next unfinished step. Existing workbook rows and personal edits are never cleared on rerun.

An empty skeleton is not production ready. The selected backend’s identity/path, seven-tab schema, validation/filter/link behavior and write/readback checks must pass. A local tracker does not require a Google identity. Reuse an explicit user's selected existing resource only after its schema/ownership is independently checked. Treat incompatible existing content as a migration, not an automatic reset.

## Interrupted discovery

Resume exact frozen window/query/page-token or employer/filter cursor and unresolved items. Reuse successful evidence with its original date; record a new check only after an actual new source read. Preserve spent attempts. A new worker or new run label cannot reset a three-attempt operation budget. A broader backlog separation requires a scoped user decision; age alone does not hide failures.

## Uncertain Google Sheets write

This is the authoritative reconciliation and settlement procedure. **Do not resend an uncertain mutation, dequeue its packets or discard its journal/owner claim.**

1. Capture a fresh [complete native snapshot](native-evidence.md#assemble-a-google-sheets-snapshot). Resolve identities by Job Key rather than old row numbers.
2. Run `python3 -m job_search_ops reconcile --root /absolute/private --journal JOURNAL_ID --snapshot /absolute/private/observed.json`.
3. Follow the returned state below. Install accepted state/receipts only after complete readback; recovery must not add a second row or sighting for the same source event.

| Observed state | Action |
| --- | --- |
| Exact planned after-state | Verify and commit the existing write without another mutation. |
| Exact before-state | Keep `awaiting_settlement`. An unchanged snapshot cannot exclude a delayed write; no automatic retry is allowed. |
| Mixed, user-edited or changed-geometry state | Preserve the conflict and queue. Review the narrow differences against the before/after journal. Reconcile only after an explicitly reviewed repair restores a verifiable before or after state. Blank inserted rows do not prove ownership. |

### Settle the current attempt

Retrying an unchanged before-state requires `reconcile --settlement /absolute/private/settlement.json`, or `sheets.reconcile(root, journal_id, snapshot, settlement)`. Evidence must identify the matching `journal_id` and **current `attempt_id`** returned by authorization/reconciliation. Its timezone-qualified `verified_at` must be on or after that attempt's `attempt_recorded_at` and no later than the current time.

Use either of these forms:

- `kind: native_terminal_failure`, with the actual `response` from that attempt containing a terminal native error code: 400, 401, 403, 404, 409, 412 or 422.
- `kind: human_reconciled`, with a genuine `human_turn_ref` and the explicit confirmation `The previous connector operation has ended; no pending call can still apply this batch.`

Both forms require the same attempt identity/time checks. **Generic errors, timeouts and 5xx responses do not prove settlement. Never manufacture human confirmation or relabel an older response as evidence for a newer attempt.**

Once marked `retryable`, capture another fresh snapshot and [authorize once](sheets-protocol.md#2-prepare-refresh-authorize-then-invoke-the-connector). Every authorization creates a new attempt ID and clears the active settlement while retaining audit history. If that call times out, evidence from the earlier attempt cannot settle it. Repeated reconciliation with the same accepted settlement is safe and does not duplicate the audit entry.

Resolve pending writes before upgrading where possible. Older pending journals without an attempt ID may still commit an exact successful readback. If unchanged or conflicting, keep the claim and pause that write for reviewed recovery; do not invent an attempt ID, delete the journal or use an old failure to authorize a retry.

### Unattempted Google Sheets plan

If a user edits or sorts before the first write, `sheets.cancel_unattempted(root, journal_id, owner)` permits a fresh plan. **It cannot cancel an attempted or uncertain mutation.** `queue.release_claim(root, workbook_id, owner)` requires the recorded owner and no unresolved journals. There is no automatic claim expiry or force-takeover API.

Do not claim Sheets offers compare-and-swap. Local ownership excludes other coordinated writers, not human editing or unrelated automation; see the [write limitation](sheets-protocol.md#3-reconcile-uncertain-outcomes).

## Uncertain local Excel write

1. Keep the private installation, original workbook, temporary candidate, original file hash, hidden sibling backup and write journal. **Never delete a journal to force a retry or promote a candidate based on an agent assertion.**
2. Rerun the same [local command](local-excel.md) and, for `local-update`, the same tracking plan. It re-reads the actual destination. If publication succeeded but receipt installation failed, recovery recognizes the published hash and installs the receipt without repeating the edit.
3. If another edit occurred, stop for reconciliation; never overwrite a changed file. Readback-only recovery is available during a pending preference pilot, but retrying an unpublished edit requires the [explicit manual pilot](preferences.md).

A saved file and an accepted queue receipt are separate steps. Keep recovery files until verification completes. Do not start a second writer or rescan completed sources just because file transfer is pending.

## Uncertain brief delivery

Retain the frozen receipt set, exact report body, snapshot and delivery intent. For chat, read the configured chat on the next wake and match the actual final assistant message to the frozen body. For email, search/read complete relevant Sent evidence and match exact report identity, recipient and body. A draft, commentary message, timeout or worker assertion is not delivery confirmation. Use the [report delivery command and evidence contract](report.md) to mark delivered only after real readback; otherwise preserve pending state. Newly accepted receipts after brief preparation belong to the next brief.

## Change ordinary preferences

Use the supported [preferences plan/apply flow](preferences.md) for search criteria, selected sources, report preferences and manual/scheduled choices. It preserves history and bindings with a resumable backup. Do not edit canonical files directly or delete the configuration guard. Tracker/account/path replacements remain migrations.

## Upgrade a deployment

1. Review release changes and configuration/schema migrations. Run offline checks in a clean staging checkout with fictional data.
2. Obtain explicit approval for any new dependency/authentication/network behavior. Use the user's existing connections; never copy credentials from another installation.
3. Back up and hash private state. Pause only the affected schedules when the user explicitly requests a maintenance pause; otherwise perform compatible read-only preparation and arrange an authorized transition. Never silently change activation, times, timezone, chat bindings or notifications.
4. Copy/verify state into a durable destination before changing references. Apply an explicit migration against a private copy and inspect differences; preserve original events, manual fields, seen history and receipts. Do not reinterpret old unknown facts as verified.
5. Validate changes with the selected backend’s actual readback. Update any selected schedule prompts using supported automation tools, verify their saved absolute paths and unchanged unrelated settings, then switch the sole writer. Avoid competing ledgers or two active deployment copies.
6. Retain an explicit rollback point and document the active schema/code version. Remove obsolete runtime copies only after verified cutover; a documentation redirect is safer than deleting unresolved history.

## Optional integrations

A source the user did not select is skipped without a connection test or coverage warning. Missing access for selected Messages or browser work affects only its dependent source/manual module, with an accurate gap. Do not expand OS permissions or switch tools to evade denial. To remove an optional MCP, use the supported configuration tooling for that exact server and preserve other entries. Leave source data untouched. Follow the selected MCP’s own installation and update instructions; this repository does not bundle its implementation.
