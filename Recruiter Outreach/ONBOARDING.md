# Set up recruiter outreach

> **Required:** Codex desktop on macOS, local file access, Python 3.10+ for private JSON records, a supported browser and your LinkedIn account. Google Drive/Sheets access is required only for the Google tracker.
> **Runs in:** Codex app. This module does not require an Application Workflow installation.
> **Computer use:** Required for live LinkedIn profiles and unsent draft preparation. You log in and perform final sends.

Give the agent this guide and use the setup request below. Setup creates private settings and creates or adopts a tracker; research, message drafting and any later batch each require a separate request. These guides create no schedules.

```text
Set up Recruiter Outreach with me using this guide. Help me choose my inputs,
verify only my selected tools and storage, and give me the linked setup summary.
Keep research and the unsent-draft pilot pending until I request them.
```

## 1. Choose your workspace and tracker

Choose a permanent private folder outside this repository and any shared export folder. Your contacts, approved copy and history stay there. Keep one installation per person; the agent will check the actual location and owner-only permissions using the [storage reference](tracker.md#set-up-storage).

Choose **local JSON** for the smallest setup, or **Google Sheets** for a visible cloud tracker. Both keep draft reservations and recovery records in private local JSON. CSV is an optional local view, not a second master.

You can adopt an existing recruiter tracker after reviewing its field mapping, contacts, history and unresolved drafts. Supply its path or workbook link. Adoption must preserve existing records; do not use the separate Application Workflow jobs tracker or another person's files.

## 2. Supply your inputs and selected tools

| Supply or choose | What the agent needs |
| --- | --- |
| Targets | Desired roles/specialties, candidate levels, excluded recruiting remits and the first company to research, if already chosen |
| Workspace and tracker | Permanent private folder; local JSON or Google Sheets; existing tracker path/link if adopting one |
| Identity and channels | IANA timezone, LinkedIn account identity, supported browser and one or more channels: InMail, LinkedIn message or connection note |
| Limits and preferences | Outstanding-draft ceiling, pilot size, research goal and the optional review/send-confirmation preferences below |
| Your copy | Verified background facts, approved message text and a shorter approved note if connection notes are selected |

Use [tools for your choices](../ONBOARDING.md#tools-for-your-choices) for general setup. Outreach needs these capabilities:

| Tool | When it is needed |
| --- | --- |
| Codex local files and Python 3.10+ | Private settings, tracker state and safe record saves; Python's standard library is enough |
| Supported browser and your LinkedIn login | Live profile checks and unsent drafts; you log in and send personally |
| Google Drive/Sheets connection | Only when you select the Google tracker |
| Available public search/page reads | Finding recruiter leads; live profiles still supply current evidence |

The agent follows the [outreach tool checks](tracker.md#outreach-tool-checks) to verify actual identity and access. Standalone outreach has no dependency on Application Workflow setup. A missing selected tool remains a recorded setup blocker; a connection never grants permission to send.

## 3. Save your choices and approved copy

Have the agent save your choices in private `settings.json` using the [agent-facing settings reference](tracker.md#agent-facing-settings). The settings and tracker remain authoritative; the final setup summary links to them.

Set a positive outstanding-draft ceiling and a pilot count no larger than it. The research count is a configurable goal, not proof of full coverage or a draft quota. Drafting uses only your selected channels; an available but unselected channel is not a fallback.

Default to qualified contacts and explicit send confirmation. Two optional preferences require explicit opt-in:

- **Review drafts for uncertain contacts:** if enabled, preserve Needs review/employer holds and label their drafts for review. Exclusions, opt-outs and prior outreach still block new drafts.
- **“Next batch” confirms sends:** if enabled after explicit discussion, that phrase confirms only the immediately preceding handed-off ready batch. It never confirms blocked contacts or unrelated older drafts. The agent records that request as the confirmation source.

Approve your own copy before any drafting. Use this neutral starting point, replacing every fact placeholder with something you can support:

```text
Subject: [Target role] opportunities at [Company]

Hi [First name],

I'm exploring [target roles] and wanted to ask whether you recruit for that area at [Company].

My background includes [one or two verified, relevant achievements].

I'd be glad to share more if that fits the teams you support.

Best,
[Your name]
```

Prepare a shorter approved connection note if that channel is selected. At runtime only the approved recipient/company substitutions may change automatically. Never copy another person's achievements, invent an application, claim a resume is attached or silently truncate copy to fit.

## 4. Check setup, then request a pilot

1. Read back private settings and storage. For new storage, verify the empty tracker; for adopted storage, verify its reviewed field mapping and preserved contacts, history and unresolved drafts. Confirm identity, destination, required fields and no unresolved migration/write issues.
2. Confirm approved copy has no fact placeholders. Mark `setup_status` as `ready` only after selected tool/storage checks pass; retain dated proof privately.
3. Request [research](research.md) for one named company or supply an explicit contact roster for the same verification process.
4. Review the roster, then separately request up to two [unsent drafts](run.md), within your configured pilot limit. Verify every prepared draft remains accessible before a larger batch.
5. Review, attach your resume where supported and send personally. Confirm the sends to update the tracker.

Tool setup alone never proves draft persistence or sending. Keep the pilot marked pending until requested and actually checked. If it is blocked, preserve its actual state and next action.

## 5. Get your setup handoff

Before ending setup, the agent must save a private [setup summary](../ONBOARDING.md#your-setup-summary) and return its location and contents. Include your selected outreach features/channels, absolute authoritative settings and state paths, tracker path or workbook/tab binding, and the chat assigned to operate them. Distinguish checks actually completed from the pending or blocked pilot. Give the exact next research request with the installed runbook and private settings paths for your chosen company, or ask for that company choice if still missing.

This summary is an index, not another configuration. If setup is incomplete, identify the missing step and the next action in the assigned chat. Update the summary after the requested pilot with its observed result.

## Change preferences

Ask the configured chat to change the named private setting. Preserve contacts, suppression, copy history, draft text and reservations. New copy needs approval; changing account, tracker or browser requires fresh identity/storage checks before use. Reducing capacity stops new allocation until existing occupied slots fit. Enabling either optional convention is explicit opt-in, never inferred from installing these guides. Refresh the setup summary's references and verification state after changes.
