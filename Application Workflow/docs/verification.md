# Verification and operating limits

> **Required:** Python 3.10+ and a disposable writable test folder; local workbook integration checks also need the [app-provided spreadsheet runtime](local-excel.md). Live checks need the selected connections.
> **Runs in:** Codex app or a local shell for offline checks; Codex app for live checks.
> **Computer use:** Only to verify a selected browser feature; offline tests use no accounts.

Normal users start with [Onboarding](../ONBOARDING.md). These checks are for the assistant or a maintainer updating the workflow.

## Local checks

From `Application Workflow/support/`:

```sh
python3 -B -m unittest discover -s tests -v
python3 -B toolkit/verify_offline.py
python3 -B scripts/verify_release.py
python3 -m job_search_ops --help
```

These commands use fictional data and do not contact accounts, create cloud resources, send messages or change schedules. Local Excel integration checks may create disposable local workbook files. They check configuration and private paths, resumable setup, tool readiness, conditional tool/resource selection, local-file safeguards, native-shaped Sheet responses, cross-source deduplication, Blind policy provenance, manual field preservation, interrupted writes and delivery checkpoints. Regression tests also cover attempt-bound settlement, durable role aliases, sticky
referral holds, the pending-pilot execution gate, complete daily recurrence, scoped
schedule readiness and disabled tracking. Tracking tests exercise accepted aliases
through the public Google commands and actual Excel files, including an old
prepared journal. Report tests cover cancelled quiet briefs, later receipts and
actionable failures with no new jobs; prompt tests execute quoted private paths.
Filesystem tests reject differently capitalized repository locations before setup
writes private data. Alias-URL tests cover saved and previously accepted alternate
URLs in both trackers, plus shared conflict guards. Pending-identity tests permute
three-source bridges before row allocation and preserve accepted rows and per-source
policies. Tracking tests compare Google and Excel row values; setup/update tests
compare generated artifacts and preserve interrupted-update recovery. Export tests
reject repository destinations reached through alternate capitalization. The toolkit tests cover parsing,
screening, source coverage, tracking and recovery.

The package check rejects unlisted files and symlinks, tolerates but excludes normal Python caches, and verifies local links, private-binding exclusions and the blank seven-tab workbook against its schema. The workbook check inspects the reviewed XML parts, metadata,
relationships and unused shared strings to catch hidden or deleted content;
unreviewed extra parts are rejected. These checks use explicit validation and remain
active with `python -O`, `python -OO` and `PYTHONOPTIMIZE`. This complements human review of changed
release assets. Setup starts from this existing workbook; rebuilding it is optional. Google setup imports it and installs open-ended summary formulas. Local setup imports and saves it through the app-provided spreadsheet runtime, then verifies the actual private file.

## Before sharing an export or clone

The complete workflow needs all files in [the reviewed inventory](../support/RELEASE_FILES.txt). A working copy is not a committed release: untracked files do not appear in a clone.

For a controlled export, review source changes and the inventory, run local checks, then:

```sh
python3 -B scripts/export_release.py /absolute/output/job-search-ops.zip
```

The destination must be new and outside the repository. The exporter refuses unexpected files (including `.env`, personal documents and unknown cache contents), packages only reviewed paths, and verifies the exact extracted archive. It prints the ZIP hash and file count. It does not commit, publish or change live state.

Extract that archive into a separate folder and run all local checks **from the extracted copy**. Exercise fictional setup outside it: Excel + rated targets/manual/chat, Google + email/portals, and tracking-only choices. Confirm unselected tools stay absent, missing live evidence stays unready, manual mode proposes no schedules and starter ratings retain historical/unknown-date provenance. Check the new preference, referral and tracking procedures. Fixtures cannot certify live behavior.

For a clone release, include the intended inventory in a reviewed commit and publish it before sharing its clone URL. Preserve unrelated user edits. Test a separate clone of that exact commit using the same steps; do not describe an untracked working tree as clone-ready.

## Checks for each new user

1. Verify only the tools, accounts and permissions required by the saved choices. Local/public-only/chat mode needs no Google account.
2. Create the selected tracker, then read back its real schema, validation, hidden key, formulas and hyperlinks.
3. Verify access from the configured chats and run a small genuine pilot of each selected discovery/tracking workflow. Check saved rows and replay handling when real qualifying records exist; report any untested path honestly.
4. In manual mode, create no schedules. Otherwise create only the chosen schedules after the pilot passes; read back their chat bindings, timezone, full recurrence, status and prompts. Check the first scheduled runs too.

For selected LinkedIn email discovery, also follow [alert onboarding](linkedin-alerts.md): verify saved searches/email delivery, the actual narrow routing rule, a real newly received alert outside Inbox, and its full-message retrieval by the configured reader. Check that representative non-alert mail is excluded. `doctor` readiness, a new label, an empty query or a manually moved old message does not prove automatic incoming routing. Keep `awaiting_first_alert` distinct from a completed zero-match discovery window. Outlook folder setup alone is not supported automated ingestion.

Local tests cannot establish these live results. Optional MCPs need their own capability checks after installation; an upstream install link does not prove a feature is present.

## Operating limits

The tested runner is Codex desktop with Python 3.10+ on macOS. The helpers use POSIX locking; other hosts and unattended cloud execution have not been certified. There is no separate background service or Google login implementation.

One coordinator owns tracker writes for one private installation. Its local claim does not lock out a human or an unrelated automation. Fresh reads, narrow writes and readback detect conflicts, but a human editing the same managed cell during an update can still race it. Manual status, notes and existing contact values are preserved during repeat sightings.

Uncertain writes or deliveries remain pending until their real outcomes are reconciled. Existing tracker adoption requires a reviewed migration; default onboarding creates a new blank tracker. Missing optional browser or Messages features affect only their dependent actions and must remain visible as gaps.
