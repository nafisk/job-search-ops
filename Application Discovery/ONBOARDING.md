# Set up Application Discovery

Use the complete repo, a [compatible Python runtime](docs/tools.md#workflow-requirements) and a durable private folder outside the repo.

## Choose your workflow

Ask one choice at a time. Reuse saved answers. Choose at least one discovery or tracking source.

| Choice | Ask or confirm |
| --- | --- |
| Job discovery | LinkedIn email alerts, referral portals, Blind companies, or a combination. Confirm the search profile below. |
| Jobs tracker | Local Excel path or Google account and workbook destination. |
| Application tracking | Gmail, Calendar, Messages, or off. Confirm the selected accounts, scope, and initial window. |
| Timing | Timezone and manual or scheduled runs. Confirm times and notifications only for requested schedules. |
| Reports | Chat by default. For self-email, confirm the recipient and permission to send. |
| Discovery export | Local Excel, Google Sheets, or off. The [three-tab export](docs/discovery-export.md) is a separate workbook. |

## Confirm the search profile

For a new discovery setup, ask for a current résumé. Accept an attachment or a private path. Reuse confirmed facts on repeat onboarding. If the person skips the résumé, ask for the work history and qualifications needed for the selected roles. Tracking-only setup can skip this step.

1. **Review experience.** Summarize engineering work the résumé supports, such as backend, frontend, full-stack or applied AI. For each relevant role family, show the employers or projects and the approximate time supported by the dates. Keep internships and full-time work distinct. Count overlapping time once in any total. Ask the person to correct the summary and clarify dates or project durations it cannot establish.
2. **Ask what to search for.** Confirm role families, internship or full-time scope, level, location and work mode, remote eligibility, and any exclusions. Confirm enrollment or graduation details if the search requires them. Ask which criteria are required and which are preferences. Separate the preferred posting experience, the highest acceptable mandatory minimum, and how to handle unstated or ranged requirements.
3. **Read the choices back before making filters.** For example, “Full-time backend or applied AI. NYC onsite or hybrid only. Mid-level preferred. Prefer postings around two years. Maximum mandatory minimum still open.” Ask whether mid-level and two years are strict before treating either as a limit.

Save confirmed facts privately. Use them for qualification checks and use the approved preferences to build search filters. See [agent setup](docs/agent-setup.md#1-establish-the-selected-workflow) for the settings.

## Prepare selected sources

- [LinkedIn alerts](docs/linkedin-alerts.md) for saved searches and verified Gmail delivery.
- [Referral portals](docs/referrals.md) for the user's companies, optional contacts and holds. Test reusable searches during the pilot.
- [Blind companies](<Blind Company Research/ONBOARDING.md>) for the target list and rating policy. Blind-only setups can skip email and referrals.

## Connect only what you need

Read the [operating rules](docs/operations.md). Check [tool access](docs/tools.md) for selected features, then follow [agent setup](docs/agent-setup.md). Show the resources and permissions before setup. Ask before adding software, permissions, or connections.

## Give this to your agent

```text
Read Application Discovery/ONBOARDING.md and guide me through the choices.
Reuse my private setup and ask only for missing information. For discovery,
start with my resume and confirm my experience and search preferences before
building filters. For referrals, ask for my companies and optional contacts,
then test and save repeatable portal searches during the pilot.
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
