# Set up Blind company research

Use the shared Application Discovery installation with local Excel or Google Sheets. Follow the [operating rules](../docs/operations.md) and [tool requirements](../../ONBOARDING.md#tools-for-your-choices). Supplied ratings require no Blind account.

```text
Set up Blind company research using this guide. Reuse my private installation
if I have one and ask one choice at a time. I authorize the tracker, chats,
documented delegation and small pilot for the features I select. Create only
schedules I request after the pilot. Save my setup summary and run requests.
```

## 1. Choose or reuse the shared installation

For a new setup, choose a durable private folder and tracker. Follow [agent setup](../docs/agent-setup.md) with `modules.blind` enabled and central available to save results. Email, referrals and tracking are optional. Manual runs and chat reports are the defaults.

For an existing setup, use the canonical config and keep its tracker, bindings and history. Use [preferences](../docs/preferences.md) for changes. Review a migration for an unbound chat or new storage/account.

## 2. Choose companies and job criteria

Use the [103-company starter](blind-companies.json) or bring a list. The starter ratings are historical and their original dates are unknown. Copy the reviewed targets to a private file and keep personal notes there. Reuse any existing private list.

Confirm the [search profile](../ONBOARDING.md#confirm-the-search-profile) and rating threshold. Confirm separate base and stretch limits for standalone research. The [runbook](run.md#setup) describes the list format and [saved portal routes](run.md#reuse-saved-portal-routes). Use [tracker admission](../docs/handoffs.md#tracker-admission) when some research matches belong only in chat.

## 3. Verify the selected tools and handoff

| Selection | Check |
| --- | --- |
| Blind research | Public page reads, browser controls, Python and private files |
| Local Excel | [Writer runtime](../docs/local-excel.md) and actual save/readback |
| Google Sheets | Central's Drive/Sheets connection, workbook identity and save/readback |
| Separate research chat | Its workspace and [handoff](../docs/handoffs.md#producer-handoff) to central |
| Scheduled runs | The requested schedule, after tool checks and the pilot |

Use `doctor --workflow blind` with the saved config and evidence. Central checks its own selected capabilities before saving. Run the [mandatory start check](run.md) before source access.

## 4. Pilot research, then save through central

1. Run a small real search and record gaps.
2. Verify the packet reached central. Have central save any accepted jobs and read them back. Record the actual [pilot evidence](../docs/agent-setup.md#5-pilot-the-selected-path).
3. For an existing preference change, follow the [replacement-pilot steps](../docs/preferences.md). Use the coordinator schedule if running in coordinated mode. A separate Blind timer needs a central run to import its packets.

Save the [private setup summary](../../ONBOARDING.md#your-setup-summary) with the actual config, list, tracker and chat bindings, verified or pending checks, timing and exact run requests.

## 5. Use the results

Ask the research chat to follow the [Blind runbook](run.md). After a standalone run, ask central to [import ready packets](../run.md) with the paths from the setup summary.

## Change preferences

Follow [preference updates](../docs/preferences.md) for company, policy and timing changes. Preserve private list and history paths. Update the setup summary after verification.
