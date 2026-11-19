# Set up Application Discovery

Use the complete repo, a [compatible Python runtime](docs/tools.md#workflow-requirements) and a durable private folder outside the repo.

## Choose your workflow

Ask one choice at a time. Reuse saved answers. Choose at least one discovery or tracking source.

| Choice | Ask or confirm |
| --- | --- |
| Job discovery | Gmail job alerts, Blind companies, or both. Save a referral list to label matches. Ask for targeted portal searches when needed. |
| Jobs tracker | Local Excel path or Google account and workbook destination. |
| Application tracking | Gmail, Calendar, Messages, or off. Confirm the selected accounts, scope, and initial window. |
| Timing | Timezone and manual or scheduled runs. Confirm times and notifications only for requested schedules. |
| Reports | Chat by default. For self-email, confirm the recipient and permission to send. |
| Discovery export | Local Excel, Google Sheets, or off. The [three-tab export](docs/discovery-export.md) is a separate workbook. |
| Tracker admission | Optional [save rule](docs/handoffs.md#tracker-admission) for stricter experience and level limits than the research scope. |

## Confirm the search profile

Follow the [résumé intake guide](docs/resume-intake.md) to draft the experience summary, confirm search preferences and prepare the private settings. Tracking-only setup can skip this step.

Set `discovery.coordinated` to `true` to run the selected Gmail and Blind sources with the same search profile. Use the main schedule if requested. Set `discovery.portals` to `true` only if you want on-demand portal searches. Referral matching uses the saved company list with either setting.

## Prepare selected sources

- [LinkedIn alerts](docs/linkedin-alerts.md) for saved searches and verified Gmail delivery.
- [Referral matching](docs/referrals.md) for employer matches. Review a matched and unmatched job in the tracker pilot. Test a reusable portal search if selected.
- [Blind companies](<Blind Company Research/ONBOARDING.md>) for the target list and rating policy. Blind-only setups can skip email and referrals.

## Connect only what you need

Read the [operating rules](docs/operations.md). Check [tool access](docs/tools.md) for selected features, then follow [agent setup](docs/agent-setup.md). Show the resources and permissions before setup. Ask before adding software, permissions, or connections.

## Give this to your agent

```text
Read Application Discovery/ONBOARDING.md and guide me through the choices.
Reuse my private setup and ask only for missing information. For discovery,
start with my resume and confirm my experience and search preferences before
building filters. For referrals, ask which companies are on my list.
Set up targeted portal searches only if I select them.
I authorize setup and a small pilot for the features I select, including their tracker,
chats, and documented handoffs. If I choose LinkedIn alerts, I authorize
the selected searches and narrow routing rules described in its setup guide.
Use manual runs and chat reports by default. Create only schedules I request
after the pilot. Save my private setup summary and first-run prompt.
```

## Before setup is complete

Confirm the selected tracker, tools, source handoffs and pilot with actual readback. Verify requested schedules after the pilot. Save the [private setup summary](../ONBOARDING.md#your-setup-summary) with the verified results, pending checks, and exact first-run request.

## Your first run

Ask your configured main chat to follow [run.md](run.md) using the installation path in your setup summary. Use [preferences](docs/preferences.md) to change an existing setup.
