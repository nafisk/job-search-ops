# Upgrade and recovery

Run commands from `Application Discovery/support/`. Keep the original private state, bindings, journals and tracker. Verify bound identities and back up state outside dated sessions.

## Interrupted setup

Read the resource journal before recreating anything. If a workbook/chat/schedule creation outcome is unknown, inspect only the selected resource: a local file and its journal, or the configured connected account/project. Match the intent, actual IDs and observed content; do not guess an ID or create a replacement to make setup proceed. Record the verified resource and resume the next unfinished step. Existing workbook rows and personal edits are never cleared on rerun.

An empty skeleton is not production ready. The selected backend’s identity/path, seven-tab schema, validation/filter/link behavior and write/readback checks must pass. A local tracker does not require a Google identity. Reuse an explicit user's selected existing resource only after its schema/ownership is independently checked. Treat incompatible existing content as a migration, not an automatic reset.

## Interrupted discovery

Resume the frozen window and saved query/page token or employer/filter cursor. Keep unresolved items, spent attempts and original observation dates. Record a new date only after a new read. Ask the user before changing backlog scope.

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

Keep the frozen receipts, body, snapshot and intent. Follow the [delivery readback steps](report.md) for every configured channel before marking delivered. Use the stored per-channel receipts to resume pending confirmations. Keep the brief pending until the exact delivery is confirmed and carry late receipts into the next brief.

## Change ordinary preferences

Use the supported [preferences plan/apply flow](preferences.md) for search criteria, selected sources, report preferences and manual/scheduled choices. It preserves history and bindings with a resumable backup. Do not edit canonical files directly or delete the configuration guard. Tracker/account/path replacements remain migrations.

## Update saved repository paths

Application Discovery owns all three discovery sources. The Blind runbook is under `Application Discovery/Blind Company Research/` and local commands run from `Application Discovery/support/`.

When upgrading an existing deployment, update repository paths in its saved chat instructions, schedule prompts and private setup summary. Follow the deployment upgrade checks below. Use the same private configuration, tracker, history and resource bindings.

## Upgrade a deployment

1. Review release changes and configuration/schema migrations. Run offline checks in a clean staging checkout with fictional data.
2. Obtain explicit approval for any new dependency/authentication/network behavior. Use the user's existing connections; never copy credentials from another installation.
3. Back up and hash private state. Pause only the affected schedules when the user explicitly requests a maintenance pause; otherwise perform compatible read-only preparation and arrange an authorized transition. Never silently change activation, times, timezone, chat bindings or notifications.
4. Copy/verify state into a durable destination before changing references. Apply an explicit migration against a private copy and inspect differences; preserve original events, manual fields, seen history and receipts. Do not reinterpret old unknown facts as verified.
5. Validate changes with the selected backend’s actual readback. Update any selected schedule prompts using supported automation tools, verify their saved absolute paths and unchanged unrelated settings, then switch the sole writer. Avoid competing ledgers or two active deployment copies.
6. Retain an explicit rollback point and document the active schema/code version. Remove obsolete runtime copies only after verified cutover; a documentation redirect is safer than deleting unresolved history.

## Adopt existing scheduled work

Use the repo for shared instructions and code. Keep deployment bindings and history on a private persistent volume or directory accessible to the chosen runner.

1. **Inventory the saved automations.** Read the prompts, target chats, status, timezone, cadence and notification policy. Record the trackers, source routes, checkpoints, pending writes, delivery history and authorized connections each prompt uses. Resolve conflicting old instructions using the latest saved choice.
2. **Map the policies.** For coordinated discovery, use one search profile and keep Blind's rating threshold. Review [tracker admission](handoffs.md#tracker-admission) separately. Copy reviewed company lists, the [Blind source CSV](<../Blind Company Research/run.md#reuse-saved-portal-routes>) and portal recipes into private inputs. Preserve dates, retries and seen history. Resolve pending saves and deliveries before switching.
3. **Check the tracker before adopting it.** Compare it with the [workbook schema](../sheets/workbook-schema.json). For a Jobs tab that ends at Notes, map existing rows to stable job keys from verified links and reconcile duplicates before importing. Add any missing **Job Sources**, **Rated Companies** and **Rated Search Coverage** tabs using the template headers. Record independently verified link evidence for the existing jobs. Preserve their statuses, notes, links and archive. Rehearse on a private copy before updating the live tracker.
4. **Verify replacement runs on a private copy.** For a tracker with the old header layout, insert one column immediately after **Application Status** and put `Referral` in row 4. Check that the hidden key, filters, formulas, links, statuses and notes survived. Pilot one referral match, one unmatched employer, one ambiguous name and one job seen by both sources. Replay the same packets. Read back the saved rows and verify that the brief still follows the selected delivery format.
5. **Switch the existing bindings.** Apply the checked tracker change. Set `discovery.coordinated` to `true` and set the private referral-list path. Give Blind's bound policy a new version and disable its separate schedule in the reviewed settings. Redirect the main schedule through the supported scheduler once the separate Blind writer is paused. Preserve the main schedule's time, timezone, notification settings and email format. Verify the saved settings and first run. Keep the old state for rollback.

## Optional integrations

A source the user did not select is skipped without a connection test or coverage warning. Missing access for selected Messages or browser work affects only its dependent source/manual module, with an accurate gap. Do not expand OS permissions or switch tools to evade denial. To remove an optional MCP, use the supported configuration tooling for that exact server and preserve other entries. Leave source data untouched. Follow the selected MCP’s own installation and update instructions; this repository does not bundle its implementation.
