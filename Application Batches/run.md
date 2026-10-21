# Open one application batch

> **Required for routine runs:** Completed [batch onboarding](ONBOARDING.md), the private ledger, installed Application Workflow configuration, Python 3.10+, current tracker/role-state reads and a supported authorized browser.
> **Runs in:** Codex app, only on an explicit human request.
> **Computer use:** Required for application pages. The user fills and submits.

**Agent procedure:** use [onboarding](ONBOARDING.md) for the user's choices and setup status. Commands and ledger fields below are implementation details for Codex.

For setup, use [Agent setup reference](#agent-setup-reference). The first explicitly requested batch may run after all non-pilot onboarding checks pass; its observed handoff completes the batch pilot. The Application Workflow initial pilot and any preference holds must already be satisfied.

**Read the private ledger and the current request before opening any page.** A daily timer, discovery result, receipt, recruiter roster or another agent cannot start this module. A current request may continue its saved scope; an unrelated later wake-up cannot resume it. Generic “continue” is sufficient only when it clearly continues this unfinished, explicitly requested batch.

## 1. Recover and reserve

1. Read [shared operating rules](<../Application Workflow/docs/operations.md>), verify the ledger's installation/tracker binding, and run `run-check --config '/absolute/private/config.json' --workflow main` from `Application Workflow/support/` using `python3 -m job_search_ops`. A held installation stays held. Before reserving or opening any role, repeat the [application criteria check](ONBOARDING.md#check-application-criteria) against current saved settings; `run-check` alone does not establish eligibility readiness.
2. Inspect `active_run`, earlier handoffs, recorded tabs and uncertain reservations. Follow [one active chat per ledger](ONBOARDING.md#4-give-the-chat-a-durable-starting-point); keep that chat's coordinator as ledger/browser owner. If another owner may still be active, stop new work until ownership is resolved.
3. Refresh current tracker status, actual links and application history. Read accepted aliases and restrictions using the command below. Match stable identities rather than row numbers; a sort or alternate URL does not create a new job.
4. Confirm the requested scope and count. First batch targets `first_total` accessible pages including carryovers. “Next five” requests five additional; a generic next batch uses `next_additional`. All allocations must fit `max_outstanding`.
5. Save the run and reserve each exact role before opening it. Count every unreleased handoff/reservation conservatively. Unknown capacity prevents new allocation but permits safe recovery of existing work.

```sh
python3 -m job_search_ops role-state --root '/absolute/private/installation' --workbook 'VERIFIED_TRACKER_ID'
```

Use actual shell-quoted bindings, including the Excel `local:` prefix. Review the returned `aliases`, `alias_urls` and `referral_restrictions` alongside the current company watchlist and user instructions; the stricter restriction wins. Follow [role restrictions](<../Application Workflow/docs/referrals.md#check-before-an-application-handoff>) for any ambiguity. This request does not release a referral hold.

## 2. Verify and open

Verify current full role requirements against the saved criteria and known factual qualifications. Skip applied/terminal jobs, duplicate applications, hard mismatches and unresolved referral routes. Unread or ambiguous eligibility stays held. Reevaluate an old scope exclusion only from fresh evidence; preserve its history. Do not collect personal form answers to open a page.

For each reserved role:

1. Inspect the actual employer/ATS application route and verify the exact company, role and requisition. Do not copy one role's link to another. A posting with an unseen Apply destination is insufficient.
2. Mark the ledger entry `opening` before the browser action. Use only the assigned browser/tab, preserve user edits, and serialize controls. Independent workers may review roles; the coordinator alone allocates slots and opens pages.
3. Inspect the result. Record actual URL/tab, accessibility and identity evidence. A reachable application page becomes `accessible`; a login wall, CAPTCHA, missing route or uncertain identity becomes `blocked`.
4. Use at most three total read-only access attempts for the same unresolved operation across workers/tabs. After a timeout inspect existing state before retrying. Preserve the spent count and exact next action; do not bypass a challenge or repeat an uncertain consequential action.
5. Save immediately after each observed result. Inaccessible attempts do not satisfy the accessible target. Continue other eligible roles in the requested scope only while capacity remains; report a smaller batch when necessary.

**Open only:** do not autofill, invoke Simplify, synchronize profiles, enter fields, upload a resume, accept agreements or press a submission control. Leave human-required steps to the user. Do not open an unrequested replacement role merely to reach a count.

## 3. Hand over and stop

Return a concise table: **company/role, requisition, application URL/tab, existing or new, accessibility, next action**. State the accessible count and outstanding capacity. List blocked/held roles separately, with the exact reason and saved continuation point.

Every successful handoff is `handoff_kind: open_only`, `prepared_verified: false`, `closed_tab_policy_eligible: false`. Opening or closing a tab never proves submission. Missing tabs remain `submission_unknown` until the user resolves them or exact independent evidence establishes an outcome.

Finish the run record and clear `active_run` only after saving its result. Accessible handoffs remain outstanding. Do not automatically open another batch, scan receipts, research recruiters, draft outreach or start a schedule.

The tracker is read-only during page opening. Keep handoff notes in the private ledger; do not mark Saved/Applied or change Notes because a tab opened. Actual tracker changes belong to separately requested [tracking](<../Application Workflow/docs/tracking.md>), through its existing writer and verified readback.

## Check all submissions

An explicit request starts reconciliation, not another batch. Read the whole known application history, tracker and registered handoffs, including older unresolved associations. Use only selected, authorized sources through [tracking](<../Application Workflow/docs/tracking.md>) and the [exact-role application helper](<../Application Workflow/support/toolkit/APPLICATIONS.md>). That helper accepts reviewed evidence; it connects no accounts and opens no pages.

Require an exact-role user report or independent native confirmation. A tracker label, timing guess or missing tab is insufficient. Preserve unknown actual submission dates. If Gmail tracking is selected, read fresh full relevant messages with the documented overlap and coverage; if it is unselected, do not access it or claim mail reconciliation. Keep evidence gaps visible.

Record confirmed outcomes and explicitly resolved/abandoned handoffs without deleting history. An explicit user decision may release a reservation; it does not assert submission. If no tracking source is enabled, a role-specific user report can resolve the private handoff, but do not force the gated tracker writer or enable sources; report that the tracker was not updated. Stop after reporting. Application-driven recruiter work requires its own request and applicable evidence checks.

## Agent setup reference

Use this section while following [onboarding](ONBOARDING.md). Read the saved configuration and [shared operating rules](<../Application Workflow/docs/operations.md>); reuse the verified tracker, criteria, permissions and source choices. Do not create another workbook or change discovery schedules.

From `Application Workflow/support/`, run the existing start check with the actual quoted configuration path:

```sh
python3 -m job_search_ops run-check --config '/absolute/private/config.json' --workflow main
```

This checks the installed configuration and pending preference-pilot holds. It does not verify current tools or the initial onboarding pilot; completed Application Workflow onboarding remains required. If it is held, follow [preference recovery](<../Application Workflow/docs/preferences.md>) before starting connected work. Setup cannot waive a pending pilot or fill in missing account access. Apply the authoritative [application criteria preflight](ONBOARDING.md#check-application-criteria) before declaring readiness or reserving/opening roles.

Read the selected tracker and [accepted role state](<../Application Workflow/docs/referrals.md#check-before-an-application-handoff>). Confirm the actual installation directory and tracker identifier, including `local:` for Excel. Job aliases, company-wide referral holds and existing application history are required inputs.

Copy [batch-state.example.json](batch-state.example.json) to a new private location, such as `<installation>/application-batches/state.json`. The directory must be outside the repository and release folder. Check its actual filesystem location, including symlinks and alternate capitalization. Give this dedicated directory owner-only access (`0700`) and its ledger, temporary files and backups owner-only access (`0600`). Never overwrite an existing ledger; recover it instead.

Populate the exact template fields:

| Field | Saved value |
|---|---|
| `workflow_config_path`, `installation_root`, `tracker_id` | Absolute configuration/root paths and the verified existing tracker ID |
| `browser.name`, `browser.session_ref` | Selected browser name and observed session/profile reference; no cookies or credentials |
| `limits` | Positive integers: `first_total: 5`, `next_additional: 5`, `max_outstanding: 20` by default; both batch sizes must fit the ceiling |
| `created_at`, `updated_at` | Actual timezone-qualified timestamps |
| `schema_version`, `active_run`, `runs`, `handoffs` | Keep version `1`, `null`, `[]`, `[]` until the first requested run |

Use [one active chat per ledger](ONBOARDING.md#4-give-the-chat-a-durable-starting-point), including submission checks, and save the actual bindings in that chat's private instructions. The template does not implement an automatic lock or background process. Keep backups and every past run private. Do not add unsupported settings to the existing Application Workflow configuration or create a schedule.

## Private ledger contract

**Agent reference:** preserve this schema and recovery protocol when creating or updating private state.

Start from the [empty template](batch-state.example.json). Keep its top-level keys, version and private bindings. `active_run` is `null` or the current run ID; `runs` and `handoffs` are arrays. Use actual timezone-qualified timestamps, stable generated run IDs and source references; no credentials or form answers.

Each `runs` entry has exactly:

```json
{
  "run_id": null,
  "request_ref": null,
  "kind": null,
  "scope": [],
  "target_count": null,
  "owner": null,
  "started_at": null,
  "finished_at": null,
  "status": null,
  "results": [],
  "next_action": null
}
```

Populate `kind` with `first_batch`, `next_batch`, `resume` or `check_submissions`; `scope` with the exact reviewed canonical role keys. For “next eligible” requests, freeze the reviewed candidate scope before allocating. `target_count` is the requested page count, or `null` for reconciliation. `request_ref` cites the human request; `owner` identifies the sole operator. `status` is `active`, `waiting_for_user`, `complete` or `blocked`. `finished_at` stays `null` until the run stops. `next_action` records the exact continuation or `null` when none remains.

Each per-run `results` entry has exactly:

```json
{
  "job_key": null,
  "classification": null,
  "outcome": null,
  "application_url": null,
  "tab_ref": null,
  "reason": null,
  "next_action": null,
  "evidence_refs": []
}
```

Use `classification: carryover|new` and `outcome: accessible|blocked|held|submission_unknown|released`. Record observed URL/tab values or `null`, plus the reason and required next action. Keep one result per canonical job within a run; a carryover references the existing handoff, never a duplicate reservation. Held candidates need no handoff entry. These observations supply the existing/new classification, accessible count and held/blocked reasons in the final table. Preserve completed runs as history even if a later run observes a different result.

Each `handoffs` entry has exactly:

```json
{
  "job_key": null,
  "company": null,
  "title": null,
  "requisition_id": null,
  "application_url": null,
  "tab_ref": null,
  "state": null,
  "attempts": 0,
  "last_observed_at": null,
  "evidence_refs": [],
  "next_action": null,
  "handoff_kind": "open_only",
  "prepared_verified": false,
  "closed_tab_policy_eligible": false,
  "history": []
}
```

One canonical `job_key` has one entry across batches. Before reserving, populate its key, company, title, reviewed route, eligibility/hold evidence and actual observation time. Retain unavailable requisitions or tab references as `null`; do not invent them. `state` is `reserved`, `opening`, `accessible`, `blocked`, `submission_unknown` or `released`. Every state except `released` consumes one outstanding slot. Held candidates that were never reserved stay in run results, without consuming a slot.

Append a `history` event for every transition with exactly `run_id`, `at`, `from`, `to`, `reason`, `evidence_refs`; `from` is `null` for the first reservation. Release requires evidence of a resolved outcome or an explicit user decision, recorded in that event. Reopening a released entry requires a new scoped request and fresh checks; prior submission evidence still prevents reapplication. Never delete rows or reset attempts to create capacity.

**Save/recovery:** the sole owner checks the latest ledger before every allocation. Save a complete previous revision privately, write a sibling temporary JSON file, parse it, then replace the ledger atomically. Keep the directory owner-only (`0700`) and all ledger, temporary and backup files owner-only (`0600`). Update `updated_at` and read back the saved run/role state. If saving fails, stop new openings and preserve tabs. After a crash, recover the ledger revision and inspect the recorded tabs before releasing ownership or allocating. A saved reservation without a result is an uncertain opening, not permission to open a duplicate. Keep backups outside the repository; this protocol does not provide an automatic process lock.
