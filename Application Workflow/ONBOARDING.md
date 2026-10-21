# Set up Application Workflow

> **Required:** Codex desktop on macOS, Python 3.10+, the complete repository in a permanent folder, and a private writable folder outside it.
> **Runs in:** Codex app; connect only the tools your choices need.
> **Computer use:** LinkedIn alerts and interactive job pages. You handle sign-in and permission prompts.

Open the complete repository in **Codex** mode and paste the setup prompt below. Use the [shared tool setup](../ONBOARDING.md#tools-for-your-choices) for installation and connection links. Codex guides you one choice at a time; you do not need to edit configuration files.

This page covers your choices and completion checks. Codex follows the [agent setup reference](docs/agent-setup.md) for the setup sequence. To choose another goal, return to [repository onboarding](../ONBOARDING.md).

## Choose your workflow

| Step | Your choice | What it adds |
| --- | --- | --- |
| 1. Tracker | Local Excel or Google Sheets | One place for every selected source. Excel needs no Google connection. |
| 2. Job discovery | Email alerts, referral portals, rated target companies, or none | Only the selected research chats. |
| 3. Tracking | Gmail, Calendar, Messages, or none | Application/interview updates from your selected sources. Each is independent. |
| 4. Timing | Manual first, or your chosen schedule | Main and rated-company runs can have separate schedules; helpers have none. |
| 5. Reports | Chat, or opted-in self-email | Chat is the default; email needs a recipient and send permission. |

**Choose at least one discovery or tracking source.** Codex reuses saved answers and asks only relevant follow-ups. For an existing installation, use [change preferences](docs/preferences.md).

## Prepare selected sources

- **LinkedIn email alerts:** you need alerts for the jobs you want. Follow [LinkedIn alerts and inbox setup](docs/linkedin-alerts.md) to create them and verify delivery. Recommended: your existing email plus a **Job Alerts** label and a narrow rule that skips Inbox. A `+jobs` address is optional. Automatic ingestion currently supports Gmail; Outlook organization is an optional section in that guide.
- **Referral portals:** choose companies using [referral setup](docs/referrals.md). Codex copies your list privately and populates both the tracker’s watchlist and the search registry.
- **Rated target companies:** choose the [103-company starter](blind-companies.json) or your own list. The starter has no personal notes. **Ratings are historical, user-supplied and not freshly verified; original dates are unknown.** Codex reviews enabled targets and copies them privately. [How this source runs](blind.md).

## Connect only what you need

[Workflow tools](docs/tools.md) lists the requirements and capability checks for these choices; [shared tool setup](../ONBOARDING.md#tools-for-your-choices) holds common installation links. Python runs the local setup and verification helpers. Local Excel also needs Codex’s app-provided spreadsheet runtime. Google Sheets needs the Drive/Sheets connection. Gmail is needed only for selected email discovery/tracking or email reports. Calendar is independent; [Mac Messages MCP](docs/messages.md) is required only if you select Messages.

Codex shows the chosen tools, permissions, tracker, chats and schedules before setup. New installations, connections and expanded permissions require your participation. A missing selected tool remains a visible gap. Existing live workflows stay untouched.

## Paste into Codex

```text
Read Application Workflow/ONBOARDING.md and follow it interactively.
Help me choose my tracker, discovery sources, tracking sources,
manual runs or schedules, and report delivery—one step at a time.
Reuse my saved preferences; ask only relevant follow-ups.

If I choose LinkedIn email discovery, follow
Application Workflow/docs/linkedin-alerts.md. Help create my chosen alerts
and narrow inbox-routing rules, reusing existing matches. I authorize those
selected setup actions. Verify real alert delivery outside Inbox and reader access.

Save my choices privately, then show the selected tools, resources and permissions.
Follow Application Workflow/docs/agent-setup.md. I authorize the selected
tracker/chats and delegation between those chats. Use manual runs and chat
reports as defaults. Create only schedules I choose, after a verified pilot.

Check actual connections and allowed operations. Do not install optional
software or broaden permissions automatically. Do not alter existing live
workflows, submit applications, contact people or book events.
Finish with the completion checklist. Return and save my private setup summary
following the repository-root ONBOARDING.md#your-setup-summary,
including my exact first-run prompt.
```

## Before setup is complete

- [ ] Choices and private installation path are saved; selected tools are verified.
- [ ] The one tracker is created, saved and read back successfully.
- [ ] Selected alert delivery, referral seed and/or rated-company copy are verified.
- [ ] Selected chats and their evidence handoffs work.
- [ ] A genuine scoped pilot saves and reports correctly; gaps remain explicit.
- [ ] Manual mode has no schedules, or requested schedules are read back after the pilot.
- [ ] Your [setup summary](../ONBOARDING.md#your-setup-summary) is returned and saved privately, with links to the canonical settings/state, tracker and selected chats, verified or pending checks, chosen schedules and exact first-run prompt.

The summary is a navigation aid. Saved settings, resource receipts and accepted pilot evidence remain authoritative; a pending selected check keeps setup incomplete for that path.

## Your first run

Paste this into the main Application Workflow chat. During setup, Codex replaces the placeholder with your actual private installation path:

```text
Read Application Workflow/run.md. Run the workflow using the saved installation
at /absolute/private/installation. Resume unfinished work, run only my selected
sources, save verified discovery and tracking updates to my one tracker, and
return my chosen report with any gaps. Do not change my settings or schedules.
```

Rated target companies may research separately, but its queued results are saved during a main run. Scheduling only that source does not schedule the main writer.
