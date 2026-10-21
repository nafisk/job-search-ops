# Set up application batches

> **Required:** A completed [Application Workflow installation](<../Application Workflow/ONBOARDING.md>), its private configuration and tracker, Python 3.10+, supported browser control and private file access.
> **Runs in:** Codex app on the installation's supported macOS host.
> **Computer use:** Required to inspect and retain application tabs. Tracker access uses the selected native Google tools or local Excel runtime.

**Give Codex this file and the absolute path to your existing private workflow configuration.** Setup records your choices; opening pages begins only when you request a batch.

## 1. Connect the existing installation

Read the saved configuration and [shared operating rules](<../Application Workflow/docs/operations.md>). Reuse the verified tracker, criteria, permissions and source choices. Do not create another workbook or change discovery schedules.

From `Application Workflow/support/`, run the existing readiness check with the actual quoted configuration path:

```sh
python3 -m job_search_ops run-check --config '/absolute/private/config.json' --workflow main
```

If it is held, follow [preference recovery](<../Application Workflow/docs/preferences.md>) before starting connected work. Setup cannot waive a pending pilot or fill in missing account access.

Read the selected tracker and [accepted role state](<../Application Workflow/docs/referrals.md#check-before-an-application-handoff>). Confirm the actual installation directory and tracker identifier, including `local:` for Excel. Job aliases, company-wide referral holds and existing application history are required inputs.

## 2. Select only the tools you need

| Tool | Why it is needed |
|---|---|
| Supported external browser control | Inspect the actual application destination and leave its tab open. Follow [browser setup](<../Application Workflow/docs/tools.md#native-tools-and-optional-additions>) and discover the host's current controls. |
| Existing tracker access | Read current jobs, statuses, links and holds through [Google Sheets](<../Application Workflow/docs/sheets-protocol.md>) or [local Excel](<../Application Workflow/docs/local-excel.md>). |
| Public search/page reads | Verify current role details and the official application route. |
| Local files and Python 3.10+ | Keep the private ledger and read accepted role aliases/restrictions with the shared CLI. |
| Selected submission sources, later | Only an explicit submission-check request needs the sources enabled in [tracking](<../Application Workflow/docs/tracking.md>). Opening pages needs neither Gmail, Calendar nor Apple Messages. |

Confirm the browser name and authorized profile/session with the user. Inspect supported controls without visiting application pages during setup. Do not install Simplify, browser libraries, new credentials or an alternate Google CLI. This workflow does not autofill forms.

## 3. Save your private ledger

Copy [batch-state.example.json](batch-state.example.json) to a new private location, such as `<installation>/application-batches/state.json`. The directory must be outside the repository and release folder. Check its actual filesystem location, including symlinks and alternate capitalization. Give this dedicated directory owner-only access (`0700`) and its ledger, temporary files and backups owner-only access (`0600`). Never overwrite an existing ledger; recover it instead.

Populate the exact template fields:

| Field | Saved value |
|---|---|
| `workflow_config_path`, `installation_root`, `tracker_id` | Absolute configuration/root paths and the verified existing tracker ID |
| `browser.name`, `browser.session_ref` | Selected browser name and observed session/profile reference; no cookies or credentials |
| `limits` | Positive integers: `first_total: 5`, `next_additional: 5`, `max_outstanding: 20` by default; both batch sizes must fit the ceiling |
| `created_at`, `updated_at` | Actual timezone-qualified timestamps |
| `schema_version`, `active_run`, `runs`, `handoffs` | Keep version `1`, `null`, `[]`, `[]` until the first requested run |

These are configurable limits, not promises of eligible jobs. The first target includes accessible carryovers; a subsequent request adds pages. All unresolved handoffs and reservations count toward the ceiling, even when their accessibility is uncertain. Lowering the ceiling never discards existing work.

The [runbook](run.md#private-ledger-contract) defines the records added during use. This is agent-managed state; the template does not implement an automatic lock or background process. Keep backups and every past run private. Do not add unsupported settings to the existing Application Workflow configuration.

## 4. Give the chat a durable starting point

Use an existing chat or create a dedicated one when the user asks. Save these bindings in its instructions:

```text
For application batches, read [absolute installed path]/Application Batches/run.md.
Use the private ledger at [absolute private path]/state.json.
Start only from my explicit request naming a batch or submission check.
Recover outstanding work before opening more pages. Never fill or submit forms.
```

Replace every bracketed value with the actual path. Keep these private instructions outside the public repository. Do not create or activate a schedule.

## 5. Review your first handoff

Ask **“Open my first batch of eligible application pages.”** Codex follows [run.md](run.md), returns the actual accessible count and lists held/blocked roles separately. You review, fill and submit.

Setup is ready when the ledger bindings are verified and the first requested handoff records exact role/tab identities. Unavailable browser or tracker access remains a setup blocker; do not label a simulated or inaccessible page as a successful pilot.
