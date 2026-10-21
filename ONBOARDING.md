# Set up the parts of your job search you need

Start with your goal. The agent guides you through the relevant choices, reuses confirmed answers and explains each connection before you use it. You do not need to edit configuration files.

## Start with your goal

| I want to… | Follow this path |
| --- | --- |
| Improve my resume | [Resume](Resume/README.md): supply your resume and the complete runbook. No repository installation or account connection is needed for a content review. |
| Improve my LinkedIn profile | [LinkedIn](LinkedIn/README.md): supply your resume and profile export/screenshots, or use an authorized browser for a live audit. Live edits require your reviewed approval. |
| Find jobs from LinkedIn alerts | [LinkedIn Job Alerts setup](<Application Workflow/ONBOARDING.md>): choose the shared jobs tracker, connect alerts and optionally select referral research or application/interview tracking. |
| Find jobs at Blind 3.5+ companies | [Blind Company Research setup](<Blind Company Research/ONBOARDING.md>): choose rated targets and use the same jobs tracker and central writer. Email alerts are optional. |
| Open application pages in batches | [Application Batches setup](<Application Batches/ONBOARDING.md>): reuse the completed shared Application Workflow installation and confirm application criteria. Saved jobs can come from either discovery path. Standalone batch-only setup is not supported in this release. |
| Find recruiters and prepare messages | [Recruiter Outreach setup](<Recruiter Outreach/ONBOARDING.md>): independent setup with its own contact tracker. Application Workflow is not required. |

**Choose either or both discovery paths.** They share one Application Workflow installation, one jobs tracker and one central writer. Blind-only setup can leave email alerts, referral portals and tracking sources off; the central chat still reviews and saves its findings before Batches can use them. Setup and pilots are completed through the shared [Application Workflow guide](<Application Workflow/ONBOARDING.md>).

You can choose more than one. Resume and supplied-content LinkedIn reviews work with an assistant that can read the supplied material; the operational workflows target **Codex desktop on macOS**. Other hosts are not certified for those workflows.

## Ask Codex to guide setup

For an operational workflow, download the **complete repository or reviewed release ZIP**, extract it to a permanent folder and open that folder in Codex. Keep it available after setup: saved instructions refer to the installed runbooks and helpers.

```text
Read ONBOARDING.md. Help me choose which job-search workflows I need,
one choice at a time. Reuse my existing setup and confirmed answers.
Explain only the tools and permissions my choices require.

Set up the features I select using their own onboarding guides. I authorize
their selected setup actions, including required trackers, chosen chats and
documented delegation. Ask before new software, connections or expanded access.
Keep existing live workflows unchanged. Do not send recruiter messages or
submit applications. Keep manual outreach and batch pilots separately requested.
Finish with my private setup summary, any blockers and the exact next request.
```

The agent follows each selected guide's setup and verification rules. This page is a route map; it does not create a universal installation, run Application Workflow checks for unrelated features, or turn setup into permission to run every module. Existing source, pilot and scheduling requirements still apply.

## Tools for your choices

Connect only what your selected work needs. Check what is already available before installing anything.

| Tool | Why and when you need it |
| --- | --- |
| [Codex desktop](https://developers.openai.com/codex/app/) and [Python 3.10+](https://www.python.org/downloads/) | Application Workflow, Blind Company Research, Batches and Outreach use the local Mac host and private file records. Their Python helpers use the standard library. Resume and supplied-content LinkedIn reviews do not require these helpers. |
| [Supported browser connection](https://learn.chatgpt.com/docs/chrome-extension) | Live LinkedIn inspection/edits, recruiter drafts, application batches and interactive job pages. You handle sign-in; the agent verifies the selected account/session and preserves existing tabs and edits. |
| [Google Drive/Sheets connection](https://learn.chatgpt.com/docs/plugins) | Required only when you choose a Google tracker. The agent verifies the exact account, workbook and permitted reads/writes. Jobs and recruiter contacts use separate trackers. |
| Codex's bundled spreadsheet runtime | Required for the local Excel jobs tracker. The agent discovers it through the app; you do not install Excel, Node packages or a spreadsheet MCP for this backend. Outreach's local JSON tracker does not need it. |
| Selected [Gmail or Calendar connections](https://learn.chatgpt.com/docs/plugins) | Gmail supports selected alert discovery, application tracking or opted-in self-email reports. Calendar supports selected interview tracking independently. Neither is required simply to open application pages or draft LinkedIn messages. |
| [Mac Messages MCP](https://github.com/carterlasalle/mac_messages_mcp) | Only for selected Messages tracking. Follow [Messages setup](<Application Workflow/docs/messages.md>) for its installation, database permission and scoped read checks. |

Research also needs the host's supported search/page readers. Availability is not proof of the right account, scope or successful operation. The selected runbook defines the actual check and readback. Missing access remains a visible gap for that operation; the feature guide determines what other work may continue. Unselected tools are not setup failures. No extra CLI, credential flow or MCP server is installed automatically.

Application-specific capability checks remain in [Application Workflow tools](<Application Workflow/docs/tools.md>); recruiter storage checks remain in [Outreach tracker setup](<Recruiter Outreach/tracker.md>). LinkedIn alert subscriptions and inbox routing have their own [setup guide](<Application Workflow/docs/linkedin-alerts.md>). [Blind Company Research](<Blind Company Research/README.md>) owns the optional [Blind starter](<Blind Company Research/blind-companies.json>); its historical ratings are not freshly verified.

## Reuse an existing setup

Provide the private configuration or ledger path for the selected workflow. Read its existing choices and verification records first. Ask only for missing information; reuse confirmed facts without silently changing another workflow's preferences or permissions.

Operational settings, evidence, contacts and history belong in a durable private folder **outside the repository and shared exports**. Check actual filesystem locations, including symlinks and case aliases. Follow the selected guide's owner-only file permissions. Preserve existing authoritative locations; adding a workflow does not authorize moving data, replacing trackers or resetting history.

Keep one authoritative configuration for each workflow. A shared summary can link those configurations, but must not become a second editable profile. Use each workflow's preference process for changes. Application Batches uses one active chat per ledger, including submission checks; see its [ownership instructions](<Application Batches/ONBOARDING.md#4-give-the-chat-a-durable-starting-point>).

## Your setup summary

At the end of operational setup, the agent returns a short handoff and saves or updates **`setup-summary.md` in your chosen private setup folder**, outside the repository. Preserve unrelated entries if that summary already exists. Resume and supplied-content LinkedIn reviews need only a handoff in the conversation; they do not require a private installation.

Include these five items:

1. **Selected workflows and current status:** what was actually verified, what still needs a login/decision/pilot, and what was not selected. Separate storage/tool readiness from a successful live run.
2. **Tracker:** the actual file path or verified workbook link for each selected tracker.
3. **Private records:** absolute links to the canonical configuration/profile, ledger and installed runbook as applicable. Keep records in their current locations; never copy credentials or private correspondence into the summary.
4. **Operating chats and timing:** the assigned existing/selected chat links or identities, their ownership roles, and manual mode or actual verified schedules. Do not create extra chats or schedules merely to fill this summary.
5. **One next request:** a ready-to-paste request with actual installed/private paths and the selected scope. If blocked, state the missing step instead of claiming the workflow is ready.

This summary is a navigation aid, not runtime configuration or evidence that a check passed. On resume, the agent reads the linked canonical settings and current verification state. A summary cannot clear a pilot hold, grant access, release a reservation or authorize a send.
