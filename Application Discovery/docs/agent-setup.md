# Agent setup reference

Follow [onboarding](../ONBOARDING.md) for the user's choices and [operating rules](operations.md) for ownership and access. Run commands from `Application Discovery/support/`.

## 1. Establish the selected workflow

Read existing private settings, permissions and resource receipts first. Use the [installation and profile examples](../support/config/README.md) for structure.

For a new setup, create a durable private installation under an existing parent outside the repo. Use owner-only directories (`0700`) and files (`0600`). Check actual paths and ownership. Write `draft-config.json` and `draft-profile.json`; reserve `config.json` and `profile.json` for the snapshots created by `init`.

For discovery, complete the [search profile conversation](../ONBOARDING.md#confirm-the-search-profile) before configuring the sources:

- Save confirmed work periods, role families and relevant qualifications in a private note referenced by `private.refs.applicant_facts`. Keep `candidate.resume_path` as the approved absolute path to an existing private résumé, or null when there is no durable path. Use the confirmed total or conservative date-based estimate for `candidate.actual_experience_years`. Record the basis and precision. Ask when there is too little information to enter a truthful number, including whether zero is correct.
- Put confirmed role families, preferred and excluded levels, and posting experience rules in `role_policy`. Set geography, remote countries, residency and relocation in `locations`. A target of two years maps to `preferred_required_years`; confirm the separate `max_required_years` before setting it.
- Save approved requirements beyond the schema, such as employment type, onsite-only scope, hard target levels or stricter limits by role family, in a private note referenced by `private.refs.search_requirements`. Label each hard requirement or preference and its scope. Use that note in search setup and [screening](../support/toolkit/SCREENING.md). For multiple role families, the shared profile should cover every approved scope and the note can narrow individual families. Review later changes with [preferences](preferences.md) and refresh affected routes and policy versions.

Prepare only selected sources. For referrals, [collect the private company list](referrals.md#choose-companies) before init. Follow [alert setup](linkedin-alerts.md) before freezing Gmail queries. Retain its raw setup evidence as `evidence/linkedin-alerts-setup.md` or an equivalent private reference. For Blind, use the [company and rating rules](<../Blind Company Research/run.md#setup>) and bind the reviewed private copy through `sources.rated_companies_path`.

```sh
python3 -m job_search_ops setup-plan --config /absolute/private/draft-config.json
```

Show the selected tracker, sources, chats, schedules and permissions. Verify the capabilities in the plan. The selected setup request authorizes its documented resources and pilot.

## 2. Check only the selected requirements

Use [tools](tools.md) to check the required identity and operations. For local Excel, verify the [Excel writer runtime](local-excel.md). Complete the separate alert delivery check when email discovery is selected.

```sh
python3 -m job_search_ops init --config /absolute/private/draft-config.json
python3 -m job_search_ops doctor --config /absolute/private/config.json
```

Use the generated `config.json` after init. Follow [preferences](preferences.md) for later changes. `doctor --workflow main` and `doctor --workflow blind` check those paths independently. Record any missing selected operation and hold work that depends on it.

## 3. Create or bind the chosen tracker

Reuse a verified binding or record intent before creating a tracker. Reconcile a creation with an uncertain outcome through [resource readback](native-evidence.md#bind-new-resources).

- **Local Excel.** Follow the [local workbook setup](local-excel.md#create-and-use-the-workbook) and verify the actual saved file.
- **Google Sheets.** Reserve the resource, import the [blank template](../sheets/job-search-tracker.xlsx) with the connector, and follow [snapshot and bootstrap](native-evidence.md#assemble-a-google-sheets-snapshot). Bootstrap only an empty template. Read the saved structure before recording the binding.

When portals are selected, [seed and verify the watchlist and portal registry](referrals.md). For a selected [discovery export](discovery-export.md), bind and check its separate workbook.

## 4. Create only the selected chats

Use the setup plan and existing bindings. Use the host's project and session tools for the selected chats. Record real IDs and workspace access. Run `prompts --config ...` after binding, then verify absolute paths and permission to delegate. Report unavailable chat or handoff access and preserve the chosen setup.

Use the [producer handoff](handoffs.md#producer-handoff) to check private staging access and acknowledgement.

## 5. Pilot the selected path

Run the [start check](operations.md#routine-operation) and use a small genuine scope for each selected branch. For referrals, [validate and save reusable portal searches](referrals.md#build-links-for-repeat-runs) from the confirmed scope. Verify actual save/readback, deduplication, manual-field preservation, and a real report. Record source gaps and scopes still pending, including `awaiting_first_alert` if applicable. Keep fixtures out of the live tracker.

Use `first-pass-record` with actual [pilot evidence](native-evidence.md#first-pass-acceptance-and-delivery). The [preference guide](preferences.md) owns replacement pilots.

## 6. Finish manually or enable chosen schedules

In manual mode, provide the main chat and first-run request. For requested schedules, use `schedule-plan` only after the relevant checks and pilot pass. Scope it with `--workflow main` or `--workflow blind` when needed. Use the selected scheduler and verify the chat, prompt, timezone, notifications, activation, and full daily recurrence. Follow [schedule boundaries](operations.md#routine-operation).

Save the [private setup summary](../../ONBOARDING.md#your-setup-summary) with canonical paths, tracker and any export, chat bindings, actual check results, schedule details, and the first-run request.
