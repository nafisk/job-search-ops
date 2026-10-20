# Run the application workflow

**Required:** completed [onboarding](ONBOARDING.md), local Codex app on macOS, Python 3.10+, private settings/state, and the tools for your selected tracker and sources.

**Runs in:** Codex with connected tools and local helpers. Public browser capability is required for discovery; interactive computer use is needed only when a source page requires it.

**Start with [onboarding](ONBOARDING.md).** This guide runs the choices saved for your installation: local Excel or Google Sheets, selected discovery/tracking sources, manual or scheduled execution, and report delivery.

The main Job Workflow chat is always the coordinator and sole tracker writer. Email Discovery and Referral Portal Search are helpers only when selected. [Rated target companies](blind.md) is a separate optional source feeding the same tracker. Helpers have no schedules; the main and Rated Target Companies chats run manually or on their individually selected schedules.

**Selected discovery → review and save → selected tracking → one report.** Tracking-only and public-research-only configurations are valid.

## Every run

**Check permission to run before source/account access or dispatch.** From `Application Workflow/support/`:

```sh
python3 -m job_search_ops run-check --config /absolute/private/config.json --workflow main
```

If held for a preference pilot, stop ordinary work and follow [the manual pilot procedure](docs/preferences.md). A timer cannot authorize its own pilot. Existing uncertain effects may be read back and reconciled; unaffected rated-company research may continue under its separate `blind` check.

1. **Read the saved choices and unfinished work.** Load the private config, generated runtime profile, resource bindings and journals. Use the read-only setup plan as the branch map; never enable a source because its tools happen to be installed. Verify only the identities, paths and permissions needed for this run. Resolve uncertain writes/sends before repeating them. Keep one writer and preserve existing history. Freeze selected source windows, using their own checkpoints and overlap; display dates in the configured timezone.

2. **Dispatch selected discovery.** If email discovery is enabled, assign [Email Discovery](helpers/email-discovery.md). If portals are enabled, assign [Referral Portal Search](helpers/referral-portals.md). Start independent branches together when available, using saved explicit dispatch authorization, real chat IDs, run ID, scope, policy version and absolute paths. If neither is selected, skip discovery dispatch. Account for ready Blind packets when Blind is enabled; do not launch an unselected source. A selected unavailable helper is a gap, not permission to change topology or duplicate its assignment.

3. **Review and save accepted results.** Read full qualification, location and availability evidence. Keep truthful applicant experience separate from search targets. Preserve each source's policy, rating provenance and referral holds. Deduplicate by employer/requisition or verified URLs and aliases, never title similarity. Use the [producer handoff](docs/handoffs.md#producer-handoff): helpers seal local evidence when they cannot write the shared queue; central verifies, archives and enqueues it, then acknowledges archival before staging is removed.

   Choose exactly one writer path: [local Excel](docs/local-excel.md) for `local_xlsx`, or the [Google Sheets protocol](docs/sheets-protocol.md) and [native evidence guide](docs/native-evidence.md) for `google_sheets`. Prepare the change, check current state, preserve manual fields, save once, and reread the actual result before accepting a receipt. Do not send local-file operations to Google or treat an XLSX export as a second master. New discovery matches start **New**. Queued or attempted work is not a verified save. A Blind stretch remains labeled under its own policy.

4. **Run only selected tracking sources.** Follow [tracking](docs/tracking.md). Gmail tracking is separate from email-alert discovery; Calendar and Apple Messages are independently selected. Skip all tracking when none are enabled. Match exact employer/role/process, retain evidence dates and uncertainty, and preserve stronger manual facts. A failed page, missing source or incomplete search cannot prove rejection, closure or no updates. Keep raw correspondence private.

5. **Report when required.** Follow [reporting](docs/report.md). A scheduled unchanged run can stay quiet under its saved preference; cancel any unattempted prepared brief before stopping. Actionable failures and required decisions still need a report, even with no new jobs. Include accepted saves from every selected source, selected tracking updates, required actions and short exceptions. Omit unselected sections. Freeze the receipt set; later saves belong to the following report. Use the saved delivery choice: chat by default, self-email only with named-recipient send authorization. Advance the delivery baseline only after actual matching readback. A manual chat report can be acknowledged on the next invocation; do not create a timer merely to confirm it.

## Continue safely after gaps

Processing may finish with exceptions while source coverage remains partial. Record the exact gap, spent attempts, resume cursor and next action. Use at most three attempts per operation across methods/workers; a reassignment cannot reset the budget. Disabled sources are **not selected**, not failures that must be fixed.

After an uncertain write or send, retain its journal, ownership and queue. Reconcile the existing effect under the selected backend's protocol; do not infer that an absent result is safe to retry. Preserve manual changes and unrelated tabs, chats and schedules.

Blind results reach the tracker only through central acceptance. In manual mode, tell the user that a central run is needed to save pending results. Scheduling Blind alone does not schedule the central writer. Never add an unrequested timer to close that gap.

Daily or manual completion does not authorize filling/submitting applications, uploading resumes, contacting recruiters/referrers, or booking/RSVPing. These remain separate explicit requests.

## Supporting details

Run local helper commands from `Application Workflow/support`. [Agent setup](docs/agent-setup.md), [tools](docs/tools.md), [operations](docs/operations.md) and [verification](docs/verification.md) contain the supporting checks. Python prepares and verifies effects; Codex uses the configured tools. Google access, when selected, stays connector-only.
