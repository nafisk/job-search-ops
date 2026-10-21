# Set up application batches

> **Required:** A completed [Application Workflow installation](<../Application Workflow/ONBOARDING.md>), its private configuration and tracker, Python 3.10+, supported browser control and private file access.
> **Runs in:** Codex app on the installation's supported macOS host.
> **Computer use:** Required to inspect and retain application tabs. Tracker access uses the selected native Google tools or local Excel runtime.

**Give Codex this file and the absolute path to your existing private workflow configuration.** Confirm your application criteria, browser/profile and preferred batch size. Codex handles the setup commands and private ledger described in the [agent setup reference](run.md#agent-setup-reference). Opening pages begins only when you request a batch.

## 1. Connect the existing installation

Codex reuses your existing tracker, criteria, permissions and source choices. It verifies the private configuration and installation paths, tracker identity, saved job aliases, company-wide referral holds and application history. It does not create another workbook or change discovery schedules.

Completed shared Application Workflow onboarding, including its initial pilot, remains required. The tracker can contain accepted jobs from [LinkedIn alerts](<../Application Workflow/README.md>), [Blind Company Research](<../Blind Company Research/README.md>) or both. Pending research packets are not batch candidates; central must save them first. Blind-only setup does not require alert or referral discovery. The [agent setup check](run.md#agent-setup-reference) checks installed configuration and pending preference-pilot holds; it does not prove current tool access or replace that pilot. A held installation follows [preference recovery](<../Application Workflow/docs/preferences.md>) before connected work. Setup cannot waive a pending pilot or fill in missing account access.

### Check application criteria

A tracking-only installation may validly omit application criteria. Confirm the roles and levels you want, where you may work, your residency and relocation choice, and your actual experience. Codex asks only for missing values or unconfirmed example defaults. Empty criteria do not mean “anything is eligible.”

**Agent preflight:** before declaring batch setup ready or reserving/opening roles, check the canonical configuration and profile for these confirmed choices:

| Required input | Where it belongs |
|---|---|
| Target role families and levels | Nonempty `role_policy.families` and `role_policy.preferred_levels` |
| Permitted locations, actual residency and relocation choice | `locations.onsite_regions` and/or `remote_countries`, plus `residency_region` and `allow_relocation` |
| Truthful experience and preferred job requirements | Known `candidate.actual_experience_years` (zero is valid), reviewed `role_policy.experience` and the selected `blind_policy` when Blind is enabled |

Save needed changes through [preference updates](<../Application Workflow/docs/preferences.md>), read back the canonical files and respect any resulting pilot hold. Do not enable discovery or change sources/schedules to satisfy this check. Until complete, hold batch readiness and new reservations/openings. Missing criteria alone need not block safe recovery or separately requested submission checks; existing execution holds and source permissions still apply.

## 2. Confirm your tools and browser

Use the shared [tools guide](../ONBOARDING.md#tools-for-your-choices) to connect only the tools your choices require. Codex checks the access below.

| Tool | Why it is needed |
|---|---|
| Supported external browser control | Inspect the actual application destination and leave its tab open. Follow [browser setup](<../Application Workflow/docs/tools.md#native-tools-and-optional-additions>) and discover the host's current controls. |
| Existing tracker access | Read current jobs, statuses, links and holds through [Google Sheets](<../Application Workflow/docs/sheets-protocol.md>) or [local Excel](<../Application Workflow/docs/local-excel.md>). |
| Public search/page reads | Verify current role details and the official application route. |
| Local files and Python 3.10+ | Keep the private ledger and read accepted role aliases/restrictions with the shared CLI. |
| Selected submission sources, later | Only an explicit submission-check request needs the sources enabled in [tracking](<../Application Workflow/docs/tracking.md>). Opening pages needs neither Gmail, Calendar nor Apple Messages. |

Confirm the browser name and authorized profile/session. Codex inspects supported controls without visiting application pages during setup. Do not install Simplify, browser libraries, new credentials or an alternate Google CLI. This workflow does not autofill forms.

## 3. Choose your limits and private history location

Choose how many pages you want and where to keep the private batch ledger. This file records reservations, open tabs and past handoffs so Codex can recover unfinished work.

| Choice | Default |
|---|---|
| First batch | Five accessible pages, including earlier pages still open |
| Next batch | Five additional pages |
| Outstanding maximum | Twenty unresolved pages or reservations |
| Private ledger location | A dedicated folder outside the repository and release, such as `<installation>/application-batches/state.json` |

These are configurable limits, not promises of eligible jobs. The first target includes accessible carryovers; a subsequent request adds pages. All unresolved handoffs and reservations count toward the ceiling, even when their accessibility is uncertain. Lowering the ceiling never discards existing work.

Codex creates or recovers the ledger using the [agent setup reference](run.md#agent-setup-reference) and [private ledger contract](run.md#private-ledger-contract). Keep it, its backups and every past run private. The ledger is agent-managed state; it does not provide an automatic lock or background process. Do not add unsupported settings to the existing Application Workflow configuration.

## 4. Give the chat a durable starting point

**One active chat per ledger, including submission checks.** Choose one existing chat, or ask to create a dedicated one. Two chats must never operate the same ledger concurrently; atomic file replacement is not a lock. To switch chats, stop the previous operator, confirm it is inactive, then recover the same ledger and tabs before continuing. If ownership is uncertain, hold new work.

Codex saves these bindings in the chosen chat's private instructions, replacing each bracketed value with its actual path:

```text
For application batches, read [absolute installed path]/Application Batches/run.md.
Use the private ledger at [absolute private path]/state.json.
This is the sole operating chat for this ledger; no concurrent batch chat.
Start only from my explicit request naming a batch or submission check.
Recover outstanding work before opening more pages. Never fill or submit forms.
```

Keep these private instructions outside the public repository. Do not create or activate a schedule.

## 5. Verify setup and your first handoff

When you want the first batch, ask **“Read the batch runbook and my private ledger. Open my first batch of eligible application pages.”** Codex follows [run.md](run.md), returns the actual accessible count and lists held/blocked roles separately. You review, fill and submit.

Setup is ready when the application criteria are confirmed and saved, one operating chat is selected, the ledger bindings are verified and the first requested handoff records exact role/tab identities. Unavailable browser or tracker access remains a setup blocker; do not label a simulated or inaccessible page as a successful pilot.

## Change preferences

Ask the operating chat to update batch limits or browser/session bindings in the private ledger, preserve history and verify the saved values. Limits must be positive integers; both batch sizes must fit the outstanding maximum. Lowering that maximum preserves existing reservations and may leave no capacity for more pages. Follow the ownership handoff above before switching chats.

Change role criteria or source choices through [Application Workflow preferences](<../Application Workflow/docs/preferences.md>), retaining its canonical files and any resulting pilot hold. These changes do not start a batch or enable a schedule.

## Your setup summary

Finish by saving or updating the shared [private setup summary](../ONBOARDING.md#your-setup-summary). It is an index to the authoritative settings and history, not an alternate configuration. Record:

- The absolute installed runbook, workflow configuration, profile and batch ledger paths, plus the authoritative tracker identifier or file path.
- The sole operating chat and selected browser/profile, including the ownership handoff rule for batch runs and submission checks.
- Verified criteria, tracker and browser access; the first handoff result, or an explicit “not yet requested” pilot gap; remaining blockers and next actions.
- The exact first request: **“Read the batch runbook and my private ledger. Open my first batch of eligible application pages.”** Name the actual installed runbook and private ledger paths in that request.

Return the summary's absolute path and the truthful setup status: ready, incomplete pending a requested pilot, or blocked with the reason.
