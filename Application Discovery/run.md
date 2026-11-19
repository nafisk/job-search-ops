# Run Application Discovery

Load the private installation from [onboarding](ONBOARDING.md). The coordinator writes the tracker and delivers the brief through the saved channel. In coordinated mode, [Gmail alerts](helpers/email-discovery.md) and [Blind research](<Blind Company Research/run.md>) share a search profile. Run [referral portal searches](helpers/referral-portals.md) on request for named companies. An existing separate Blind schedule follows its saved plan until cutover.

Use sub-agents for independent source collection and evidence review where supported. Give each worker a distinct scope and evidence path. Use the coordinator's model at high reasoning when available. Never run a sub-agent at ultra reasoning. The coordinator owns the shared queue, tracker writes and report delivery.

## Every run

**Run this check before source access or dispatch.** Run it from `Application Discovery/support/`.

```sh
python3 -m job_search_ops run-check --config /absolute/private/config.json --workflow main
```

If a preference change holds the workflow, follow the [manual pilot procedure](docs/preferences.md). An existing uncertain effect can still be reconciled. Unaffected Blind research can proceed under its own `blind` check.

1. **Load the run plan.** Read the private config, generated runtime profile, bindings and unfinished journals. Verify identities and access for this run. Reconcile uncertain effects, then freeze each selected source window using its checkpoint, overlap and configured timezone.
2. **Collect findings.** Start `daily_discovery`, or the selected source named in a manual request. Pass the run ID, scope, cutoff, policy version and absolute paths. Check the Blind gate, then start Gmail alerts and Blind together when both are selected. Use the authorized [fallback](docs/handoffs.md#producer-handoff) if needed. At the deadline, record missing results and prepare the save from ready packets, including any from separate Blind runs. Packets that arrive after preparation wait for the next run.
3. **Screen and save.** Review full postings using [screening](support/toolkit/SCREENING.md) and any [tracker admission rule](docs/handoffs.md#tracker-admission). Keep source policy, Blind rating provenance and stretch labels. Deduplicate by employer and requisition or verified URLs and aliases. Verify and archive any [handoff staged outside the shared queue](docs/handoffs.md#producer-handoff) before acknowledging it. Use the selected writer, [local Excel](docs/local-excel.md) or [Google Sheets](docs/sheets-protocol.md), and confirm the save by readback. New matches start **New**.

   If referral matching is enabled, write **Available** for a unique employer match and leave the field blank otherwise. Report `referral_gap` and ambiguous employers in `referral_review`. Qualified jobs are saved either way.

   After the save, [export accepted jobs](docs/discovery-export.md) if a destination is configured. For an export-only request, use that guide directly. Report export failures alongside the tracker outcome.
4. **Track applications if selected.** Use the [tracking runbook](docs/tracking.md) for the selected Gmail, Calendar or Apple Messages sources. Match the exact employer and process, keep evidence dates and preserve stronger manual facts.
5. **Report verified results.** Follow the [brief and delivery steps](docs/report.md). Use compact filters and public links for saved jobs. Include selected tracking updates and surface actionable gaps separately. The saved notification preference controls quiet scheduled runs. Report actionable failures and decisions even when there are no new jobs. Confirm delivery against the frozen brief before advancing the baseline.

## Continue safely after gaps

Record the gap, attempts spent, resume cursor and next action. Share the three-attempt budget across methods and workers. See [source coverage and retry rules](docs/operations.md#completion-and-source-gaps).

Keep the journal, ownership and queue after an uncertain write or send. Follow [recovery](docs/upgrade-and-recovery.md) before retrying. If standalone Blind queues findings, tell the user when central will import them or how to request a manual import.

Application submission, résumé uploads, outreach, bookings and RSVPs each need a separate request.

## Supporting details

See [agent setup](docs/agent-setup.md), [tools](docs/tools.md) and [verification](docs/verification.md). Use the [native evidence guide](docs/native-evidence.md) for Google connector readback.
