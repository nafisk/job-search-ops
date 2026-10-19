# Local workflow helpers

**Required:** Python 3.10+; use the private runtime profile created during [setup](../../ONBOARDING.md). No extra Python packages.  
**Runs in:** Codex’s local terminal. These helpers do not connect accounts or control the computer.

Users start with [onboarding](../../ONBOARDING.md). Agents use this library only where a runbook calls for it. The main workflow owns live reads, source review, tracker writes and reports.

## What remains here

| Helper | Why it is needed | Used by |
|---|---|---|
| [Profile validation](PROFILE.md) | Check saved criteria, paths and selected integrations | Setup and every selected source |
| [Email extraction](ALERTS.md) + [screening](SCREENING.md) | Account for all alert cards and check full job requirements | [Email helper](../../helpers/email-discovery.md) |
| [Portal registry](PORTALS.md) + [retries](RETRIES.md) | Validate search routes and preserve spent attempts/cursors | [Portal helper](../../helpers/referral-portals.md) and source reads |
| [Applications](APPLICATIONS.md), [lifecycle](LIFECYCLE.md), [interviews](INTERVIEWS.md) | Keep submissions, responses and interview facts separate | [Tracking](../../docs/tracking.md) |
| [Coverage](COVERAGE.md) + [shared validation](CONTRACTS.md) | Preserve source gaps and validate evidence bindings | Selected tracking and other helpers |

`sheet_values.py` is the shared literal-value/URL validator used by extraction, screening and portal checks. `examples/` contains two fictional profiles. `tests/` contains regression checks for the retained helpers; it is not part of a daily run.

## What lives elsewhere

The [workflow support CLI](../README.md) manages setup, the shared queue, tracker journals, verified saves and delivery receipts. Do not substitute an old simulated storage or delivery adapter. Native access comes from the selected tools in [tool requirements](../../docs/tools.md).

Personal profiles, working company lists/notes, resumes, evidence and history belong outside the repository. The approved [starter list](../../blind-companies.json) is copied and reviewed during onboarding; its historical ratings are not freshly verified. Example values never authorize access or stand in for live evidence.

## Maintenance only

Run `python3 -B verify_offline.py` from this folder to check the exact file list and test a fresh temporary copy. See [verification details](TESTING.md). `SHAREABLE_FILES.txt` is the reviewed inventory, not an installer or exporter.
