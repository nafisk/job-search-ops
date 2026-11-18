# Set up application batches

Give the agent the absolute path to your private [Application Discovery configuration](<../Application Discovery/ONBOARDING.md>). Confirm your application criteria, supported browser profile and batch limits. The agent prepares the ledger using the [setup reference](run.md#agent-setup-reference). Request a batch separately.

## 1. Connect the existing installation

Reuse the completed shared setup and pilot. Verify the installation, tracker, saved job aliases, company-wide holds and application history. Use only accepted jobs saved by central. Check current tool access separately from the [setup check](run.md#agent-setup-reference). Resolve any [preference-pilot hold](<../Application Discovery/docs/preferences.md>) before connected work.

### Check application criteria

Before marking setup ready or reserving or opening roles, confirm these values in the canonical configuration and profile. Ask only for missing or unconfirmed values. A tracking-only installation may omit them, so check even if its pilot passed.

| Confirm | Required values |
| --- | --- |
| Roles and levels | Nonempty `role_policy.families` and `role_policy.preferred_levels` |
| Where the user can work | `locations.onsite_regions` or `remote_countries` or both, plus `residency_region` and `allow_relocation` |
| Experience and job requirements | Known `candidate.actual_experience_years` (zero is valid), reviewed `role_policy.experience`, and `blind_policy` if enabled |

Use [preferences](<../Application Discovery/docs/preferences.md>) to save changes. Read back the canonical files and follow any resulting pilot hold. Preserve discovery sources and schedules. Missing criteria block readiness and new pages or reservations. Safe recovery and separate submission checks can continue within existing holds and permissions.

## 2. Confirm your tools and browser

Use the shared [tools guide](../ONBOARDING.md#tools-for-your-choices) to connect only the tools your choices require. The agent checks the access below.

| Tool | Why it is needed |
|---|---|
| Supported external browser control | Inspect the actual application destination and leave its tab open. Follow [browser setup](<../Application Discovery/docs/tools.md#native-tools-and-optional-additions>) and discover the host's current controls. |
| Existing tracker access | Read current jobs, statuses, links and holds through [Google Sheets](<../Application Discovery/docs/sheets-protocol.md>) or [local Excel](<../Application Discovery/docs/local-excel.md>). |
| Public search/page reads | Verify current role details and the official application route. |
| Local files and Python 3.10+ | Keep the private ledger and read accepted role aliases/restrictions with the shared CLI. |
| Selected submission sources, later | Only an explicit submission-check request needs the sources enabled in [tracking](<../Application Discovery/docs/tracking.md>). Opening pages needs neither Gmail, Calendar nor Apple Messages. |

Confirm the browser name and authorized profile/session. The agent inspects supported controls without visiting application pages during setup. Do not install Simplify, browser libraries, new credentials or an alternate Google CLI. This workflow does not autofill forms.

## 3. Choose your limits and private history location

Choose how many pages you want and where to keep the private batch ledger. This file records reservations, open tabs and past handoffs so the agent can recover unfinished work.

| Choice | Default |
|---|---|
| First batch | Five accessible pages, including earlier pages still open |
| Next batch | Five additional pages |
| Outstanding maximum | Twenty unresolved pages or reservations |
| Private ledger location | A dedicated folder outside the repository and release, such as `<installation>/application-batches/state.json` |

These are configurable limits, not promises of eligible jobs. The first target includes accessible carryovers; a subsequent request adds pages. All unresolved handoffs and reservations count toward the ceiling, even when their accessibility is uncertain. Lowering the ceiling never discards existing work.

The agent creates or recovers the ledger using the [agent setup reference](run.md#agent-setup-reference) and [private ledger contract](run.md#private-ledger-contract). Keep it, its backups and every past run private. The ledger is agent-managed state. It does not provide an automatic lock or background process. Do not add unsupported settings to the existing Application Discovery configuration.

## 4. Give the chat a durable starting point

**One active chat per ledger, including submission checks.** Choose one existing chat, or ask to create a dedicated one. Two chats must never operate the same ledger concurrently; atomic file replacement is not a lock. To switch chats, stop the previous operator, confirm it is inactive, then recover the same ledger and tabs before continuing. If ownership is uncertain, hold new work.

The agent saves these bindings in the chosen chat's private instructions, replacing each bracketed value with its actual path:

```text
For application batches, read [absolute installed path]/Application Batches/run.md.
Use the private ledger at [absolute private path]/state.json.
This is the sole operating chat for this ledger; no concurrent batch chat.
Start only from my explicit request naming a batch or submission check.
Recover outstanding work before opening more pages. Never fill or submit forms.
```

Keep these private instructions outside the public repository. Do not create or activate a schedule.

## 5. Verify setup and your first handoff

When you want the first batch, ask **“Read the batch runbook and my private ledger. Open my first batch of eligible application pages.”** The agent follows [run.md](run.md), returns the actual accessible count and lists held/blocked roles separately. You review, fill and submit.

Setup is ready when the application criteria are confirmed and saved, one operating chat is selected, the ledger bindings are verified and the first requested handoff records exact role/tab identities. Unavailable browser or tracker access remains a setup blocker; do not label a simulated or inaccessible page as a successful pilot.

## Change preferences

Ask the operating chat to update batch limits or browser/session bindings in the private ledger, preserve history and verify the saved values. Limits must be positive integers; both batch sizes must fit the outstanding maximum. Lowering that maximum preserves existing reservations and may leave no capacity for more pages. Follow the ownership handoff above before switching chats.

Change role criteria or source choices through [Application Discovery preferences](<../Application Discovery/docs/preferences.md>), retaining its canonical files and any resulting pilot hold. These changes do not start a batch or enable a schedule.

## Your setup summary

Finish by saving or updating the shared [private setup summary](../ONBOARDING.md#your-setup-summary). It is an index to the authoritative settings and history, not an alternate configuration. Record:

- The absolute installed runbook, workflow configuration, profile and batch ledger paths, plus the authoritative tracker identifier or file path.
- The sole operating chat and selected browser/profile, including the ownership handoff rule for batch runs and submission checks.
- Verified criteria, tracker and browser access; the first handoff result, or an explicit “not yet requested” pilot gap; remaining blockers and next actions.
- The exact first request: **“Read the batch runbook and my private ledger. Open my first batch of eligible application pages.”** Name the actual installed runbook and private ledger paths in that request.

Return the summary's absolute path and the truthful setup status: ready, incomplete pending a requested pilot, or blocked with the reason.
