# Set up Application Discovery

Use the full repo, a [compatible Python runtime](docs/tools.md#workflow-requirements) and a durable private folder outside the repo.

## Choose your workflow

Reuse saved answers and ask one choice at a time. Select at least one discovery or tracking source.

| Choice | Confirm |
| --- | --- |
| Discovery | Gmail job alerts, Blind companies, or both. A referral list adds employer labels and can support searches for named companies. |
| Tracker | A local Excel path or the Google account and workbook destination. |
| Tracking | Gmail, Calendar, Apple Messages, or off. Confirm scope and the initial window for selected sources. |
| Timing and reports | Timezone, manual or scheduled runs, and chat or self-email. Confirm schedule details and send permission when selected. |
| Export | Off, local Excel or Google Sheets. The [three-tab export](docs/discovery-export.md) uses a separate workbook. |
| Tracker admission | An optional [save rule](docs/handoffs.md#tracker-admission) for stricter experience or level limits than the research scope. |

## Confirm the search profile

For discovery, use [résumé intake](docs/resume-intake.md) to confirm experience, preferences and search requirements. Tracking-only setup can skip this.

Set `discovery.coordinated` to `true` for a shared Gmail and Blind search profile. Use the main schedule if requested. Set `discovery.portals` to `true` for on-demand portal searches. The private list supports referral labels whether portal searches are enabled or disabled.

## Prepare selected sources

- [LinkedIn alerts](docs/linkedin-alerts.md) verifies saved searches and Gmail delivery.
- [Referral setup](docs/referrals.md) covers employer labels and reusable portal searches.
- [Blind setup](<Blind Company Research/ONBOARDING.md>) covers company choices and rating policy.

## Connect only what you need

Follow [agent setup](docs/agent-setup.md) to check the [selected tools](docs/tools.md) and show the planned resources. The [operating rules](docs/operations.md) cover setup permissions.

## Give this to your agent

```text
Read Application Discovery/ONBOARDING.md. Reuse my saved choices and ask only
for missing information. For discovery, start with my résumé and confirm my
search criteria. Ask for my referral companies if I want matching.

I authorize setup and a small pilot for the features I select, including the
tracker, chats and documented handoffs. If I choose LinkedIn alerts, I authorize
the selected searches and narrow routing rules in its setup guide.

Use manual runs and chat reports by default. Create only schedules I request
after the pilot. Save my setup summary with the first-run request.
```

## Before setup is complete

Verify the tracker, handoffs and pilot by readback. For referral labels, check one match and one unmatched job. Verify any requested schedules after the pilot. Record verified results and pending work in the [private setup summary](../ONBOARDING.md#your-setup-summary).

## Your first run

Ask the configured main chat to follow [run.md](run.md) with the installation path from your summary. Use [preferences](docs/preferences.md) for later changes.
