# Change your saved preferences

> **Required:** An initialized version-two installation, its private settings and Python 3.10+.
> **Runs in:** Codex app; local updates use the CLI, schedule changes use Codex automation tools.
> **Computer use:** None unless a newly selected tool requires connection setup.

Ask Codex: **“Update my job-workflow preferences using this guide. Show the changes and preserve my tracker and history.”** Follow [operating rules](operations.md). No re-onboarding or fresh tracker is needed for ordinary settings changes.

Supported changes include search criteria, disabling selected sources, report preferences and manual-to-scheduled execution. The updater retains tracker/chat IDs, accepted rows, receipts, source history and first-pass evidence. Changes to accounts, tracker provider/path, installation location or new unbound helper chats need a separate reviewed migration; this command stops instead of guessing those bindings.

## Agent procedure

Commands run from `Application Workflow/support/`.

1. Read the installed `config.json` and `profile.json`. Make separate private **`update-config.json` and `update-profile.json`** drafts; point the draft config at the draft profile. Change only the user's requested choices. Keep canonical files unchanged until apply.
When changing search criteria, locations or experience ceilings, increment `role_policy.version`. If rated target companies are enabled, also increment `blind_policy.version`; changing rated-only rules requires its version bump. This prevents a late producer packet from silently reusing old qualification decisions. Disabling an integration also sets its profile `enabled`/`required` to false and its connection/identity fields to null; the private backup retains prior bindings.

2. Finish unresolved writes and report delivery first. Before changing discovery criteria or disabling discovery, save and report queued packets under their original policy. Never delete queues or journals to make an update pass.
3. Review the plan:

```sh
python3 -m job_search_ops preferences-plan --config /absolute/private/config.json --candidate /absolute/private/update-config.json --output /absolute/private/preferences-plan.json
```

The plan shows exact changed fields, selected tool requirements and schedule actions. Preserve the returned `expected_digest`; it binds the plan to the current installation. New permissions/connections remain subject to the user's selected authorization.

4. Apply that exact reviewed plan, substituting its actual digest:

```sh
python3 -m job_search_ops preferences-apply --config /absolute/private/config.json --plan /absolute/private/preferences-plan.json --expected-digest EXPECTED_DIGEST
```

This updates only private local settings, execution plan, source policies, runtime profile and prompts. It writes a private backup before changes. If interrupted, rerun **the same command and plan**; ordinary queue work is blocked while the transaction is unfinished. Stale plans or unexpected file changes stop for inspection. The `.setup.lock` file is now a persistent operating-system lock; its presence alone is normal and process termination releases ownership. Do not delete it. Unrecognized legacy lock contents require inspection before migration. A completed replay does not repeat changes.

5. Recheck selected tools with `doctor`, then run each workflow listed in `pilot_required`. Record its actual new acceptance through `first-pass-record`, with `preferences_update_id` in the native evidence. Earlier first passes remain in history; the new acceptance is stored under the update’s `pilot_passes`. Changed operational scope blocks scheduling/activation until that pilot is accepted. Timing-only changes can reuse unaffected pilot evidence. A requested pause remains available immediately.

## Schedules

Local apply does **not** activate, pause, recreate or delete any automation.

- **No schedule bound:** a requested time produces `create_after_doctor_and_pilot`. Follow [agent setup](agent-setup.md#6-finish-manually-or-enable-chosen-schedules), then use `schedule-plan` and supported Codex automation tools.
- **Existing schedule:** the plan names its exact resource ID and before/after request. Read that automation through Codex, reconcile any drift, and update only reviewed fields. Retain its ID, chat, timing, activation and notification settings unless that field was requested to change. Disabling a scheduled workflow produces a requested pause, not deletion.
- Record actual saved readback with `preferences-schedule-record --config /absolute/private/config.json --update UPDATE_ID --workflow main --evidence /absolute/private/schedule-evidence.json --observation OBSERVATION_ID`. Use `blind` for the rated target company source. The [native evidence](native-evidence.md) must bind the installation and `preferences_update_id`, exact automation ID and saved prompt/timing/status. Pending reconciliation stays visible and prevents another preferences update or new schedule plan.

If an automation update has an unknown outcome, read back that same ID before any retry. Do not create a replacement. Retain the local update backup and pending schedule actions until resolved.
