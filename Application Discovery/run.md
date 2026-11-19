# Run Application Discovery

Complete [onboarding](ONBOARDING.md) and load the private settings. Follow the saved source, tracker, timing and delivery choices.

The coordinator owns tracker writes and the brief. Use `daily_discovery` in the private execution plan. In coordinated mode, Gmail alerts and [Blind research](<Blind Company Research/run.md>) share a search profile and run together. Run [referral portal searches](helpers/referral-portals.md) when the user asks for named companies. Existing installations that use a separate Blind schedule follow their saved plan until cutover.

## Every run

**Check permission to run before source/account access or dispatch.** From `Application Discovery/support/`:

```sh
python3 -m job_search_ops run-check --config /absolute/private/config.json --workflow main
```

If held for a preference pilot, stop ordinary work and follow [the manual pilot procedure](docs/preferences.md). A timer cannot authorize its own pilot. Existing uncertain effects may be read back and reconciled; unaffected rated-company research may continue under its separate `blind` check.

1. **Read the saved choices and unfinished work.** Load the private config, generated runtime profile, resource bindings and journals. Use the read-only setup plan as the branch map; never enable a source because its tools happen to be installed. Verify only the identities, paths and permissions needed for this run. Resolve uncertain writes/sends before repeating them. Keep one writer and preserve existing history. Freeze selected source windows, using their own checkpoints and overlap; display dates in the configured timezone.

2. **Dispatch discovery.** Start the sources in `daily_discovery`, or the selected source the user named for a manual run. Give each producer the run ID, scope, cutoff, policy version and absolute paths. Start [Email Discovery](helpers/email-discovery.md) and Blind together when selected. Check the Blind gate before it starts. At the run's collection deadline, note any missing results and prepare the save from the ready queue. Packets queued after preparation go to the next run. Use the saved [fallback](docs/handoffs.md#producer-handoff) if a helper is unavailable. For installations with separate Blind runs, drain their ready packets.

3. **Review and save accepted results.** Use [screening](support/toolkit/SCREENING.md) with the full posting and any configured applicant facts and search requirements. Apply [tracker admission](docs/handoffs.md#tracker-admission) when configured. Preserve each source's policy, rating provenance and referral holds. Deduplicate by employer/requisition or verified URLs and aliases, never title similarity. Use the [producer handoff](docs/handoffs.md#producer-handoff): helpers seal local evidence when they cannot write the shared queue; central verifies, archives and enqueues it, then acknowledges archival before staging is removed.

   Choose exactly one writer path: [local Excel](docs/local-excel.md) for `local_xlsx`, or the [Google Sheets protocol](docs/sheets-protocol.md) and [native evidence guide](docs/native-evidence.md) for `google_sheets`. Prepare the change, check current state, preserve manual fields, save once, and reread the actual result before accepting a receipt. Do not send local-file operations to Google or treat an XLSX export as a second master. New discovery matches start **New**. Queued or attempted work is not a verified save. A Blind stretch remains labeled under its own policy.

   If referral matching is enabled, the writer checks qualified jobs against the private list after deduplication. It marks **Available** or **On hold** in Jobs. Check `referral_review` in the save result for ambiguous employers and report any that need a decision in the existing exceptions section. Treat an unreadable list as a save gap and keep the queue for recovery.

   Read the saved destination using [discovery export](docs/discovery-export.md) after the tracker save. Publish the accepted postings if a destination is selected. For an export-only request, go directly to that guide and export previously accepted postings. Report any export failure with its verified tracker outcome.

4. **Run only selected tracking sources.** Follow [tracking](docs/tracking.md). Gmail tracking is separate from email-alert discovery; Calendar and Apple Messages are independently selected. Skip all tracking when none are enabled. Match exact employer/role/process, retain evidence dates and uncertainty, and preserve stronger manual facts. A failed page, missing source or incomplete search cannot prove rejection, closure or no updates. Keep raw correspondence private.

5. **Report when required.** Follow [reporting](docs/report.md). A scheduled unchanged run can stay quiet under its saved preference; cancel any unattempted prepared brief before stopping. Actionable failures and required decisions still need a report, even with no new jobs. Include accepted saves from every selected source, selected tracking updates, required actions and short exceptions. Omit unselected sections. Freeze the receipt set; later saves belong to the following report. Use the saved delivery choice: chat by default, self-email only with named-recipient send authorization. Advance the delivery baseline only after actual matching readback. A manual chat report can be acknowledged on the next invocation; do not create a timer merely to confirm it.

## Continue safely after gaps

Processing may finish with exceptions while source coverage remains partial. Record the exact gap, spent attempts, resume cursor and next action. Use at most three attempts per operation across methods/workers; a reassignment cannot reset the budget. Disabled sources are **not selected**, not failures that must be fixed.

After an uncertain write or send, retain its journal, ownership and queue. Reconcile the existing effect under the selected backend's protocol; do not infer that an absent result is safe to retry. Preserve manual changes and unrelated tabs, chats and schedules.

Blind results reach the tracker through central acceptance. If a standalone/manual Blind run queues results, tell the user how to trigger central to save them. Only create schedules the user selected.

Daily or manual completion does not authorize filling/submitting applications, uploading resumes, contacting recruiters/referrers, or booking/RSVPing. These remain separate explicit requests.

## Supporting details

Run local helper commands from `Application Discovery/support`. [Agent setup](docs/agent-setup.md), [tools](docs/tools.md), [operations](docs/operations.md) and [verification](docs/verification.md) contain the supporting checks. Python prepares and verifies effects. The agent uses the selected tools. Google access, when selected, stays connector-only.
