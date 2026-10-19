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

1. Keep the write journal and owner claim. Do not resend its mutation or dequeue its packets.
2. Obtain fresh native metadata and bounded CellData for every affected/preserved identity, table/link constraint and expected insertion area. Resolve rows by Job Key, not old row numbers.
3. Run `python3 -m job_search_ops reconcile --root /absolute/private --journal JOURNAL_ID --snapshot /absolute/private/observed.json`.
4. Exact after-state is verified without another insertion. An unchanged before-state remains `awaiting_settlement`: an apparently absent result after a timeout does not exclude a delayed write. Supply real terminal native failure or explicit human settlement evidence through `reconcile --settlement /absolute/private/settlement.json` before a fresh authorization can permit a retry. It must identify this `journal_id` and the **current `attempt_id`** returned by authorization/reconciliation. Its timezone-qualified `verified_at` must be on or after this attempt's `attempt_recorded_at`, and not in the future. See the [settlement evidence contract](sheets-protocol.md#3-reconcile-uncertain-outcomes).
5. Install accepted state/receipts only after complete readback. Replay must not add another row or another sighting for the same source event.

Every new authorization creates a new attempt ID. If that call times out, an older call's failure or human confirmation cannot settle it. Keep the actual response associated with its original attempt; do not change its identity or timestamp to make a retry pass. Partial, duplicate, changed-geometry or conflicting state remains unresolved. Re-read/re-plan only a specifically reviewed repair and preserve manual changes.

Before upgrading a writer, resolve its pending writes where possible. An older pending journal without an attempt ID can still recover through an exact successful readback. If its state is unchanged or conflicting, keep its owner claim and pause that write for a reviewed recovery; do not invent an attempt ID, delete the journal or use an old failure to authorize a retry.

Do not claim Sheets offers compare-and-swap. Local ownership excludes other coordinated writers, not human editing or unrelated automation.

## Uncertain local Excel write

Follow [local Excel recovery](local-excel.md). Keep the original workbook, temporary candidate, original file hash and write journal until the outcome is verified. Re-read the actual destination before retrying; never promote a candidate or overwrite a changed file based on an agent assertion. A saved file and an accepted queue receipt are separate steps. Do not start a second writer or rescan completed sources just because the file transfer is pending.

## Uncertain brief delivery

Retain the frozen receipt set, exact report body, snapshot and delivery intent. For chat, read the configured chat on the next wake and match the actual final assistant message to the frozen body. For email, search/read complete relevant Sent evidence and match exact report identity, recipient and body. A draft, commentary message, timeout or worker assertion is not delivery confirmation. Mark delivered only after real readback; otherwise preserve pending state. Newly accepted receipts after brief preparation belong to the next brief.

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
