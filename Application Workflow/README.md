<div align="center">

<h1>🔁 Application Workflow</h1>

<p><strong>Find relevant jobs. Keep applications and interviews in one place.</strong></p>

<p>Guided setup, selected job sources, and one shared tracker.</p>

<p>
  <img src="https://img.shields.io/badge/Runs_in-Codex_App-2563eb?style=flat-square" alt="Runs in: Codex app">
  <img src="https://img.shields.io/badge/Tracker-Excel_or_Google_Sheets-475569?style=flat-square" alt="Tracker: Excel or Google Sheets">
  <img src="https://img.shields.io/badge/Setup-guided-16a34a?style=flat-square" alt="Guided setup">
</p>

<p><a href="ONBOARDING.md">Start onboarding</a> · <a href="run.md">Run the workflow</a> · <a href="../README.md">All runbooks</a></p>

</div>

---

## 🚀 Set up your copy

1. Open this repo in **Codex** and follow [onboarding](ONBOARDING.md).
2. Choose **Excel or Google Sheets**, job sources, and tracking features.
3. Connect selected tools and set up [LinkedIn alerts](docs/linkedin-alerts.md) if needed.
4. Review a first run; activate only the schedule you chose, or continue manually.

> [!TIP]
> Choose only what you need. Gmail, Calendar, and Messages are independent options. Your settings stay private.

## Every run

1. Read your preferences and resume unfinished work.
2. Ask the selected helpers to find and check jobs.
3. Merge verified results into your **one tracker**, preserving your edits.
4. Check selected sources for application and interview updates.
5. Return one report with new jobs, updates, actions, and gaps.

**The main chat saves; helpers research.** Helpers have no timers. Rated target companies can run separately, with results saved during the next main run. [Shared operating rules](docs/operations.md) explain permissions, evidence and recovery boundaries.

## 📚 Start and run

| Instructions | What they do | How they run |
| --- | --- | --- |
| [Onboarding](ONBOARDING.md) | Choose features; create your tracker, chats, and optional schedules. | Codex; user handles sign-in/permissions. |
| [Main workflow](run.md) | Coordinate, save, track, and report. | Codex + selected tools. |
| [Email discovery](helpers/email-discovery.md) | Read alerts; verify job descriptions. | Gmail; browser as needed. |
| [Referral portals](helpers/referral-portals.md) | Search chosen companies; preserve referral holds. | Web tools; computer use for interactive pages. |
| [Rated target companies](blind.md) | Search your rated-company list using its fit policy. | Web tools; computer use as needed. |

## Optional features and setup details

| Instructions | What they do | Required access |
| --- | --- | --- |
| [Referral setup](docs/referrals.md) | Populate one company list into the watchlist and search registry. | Selected tracker + local helpers. |
| [Change preferences](docs/preferences.md) | Update choices while preserving your tracker and history. | Codex + existing bindings. |
| [LinkedIn alert setup](docs/linkedin-alerts.md) | Create alerts and inbox filters. | LinkedIn computer use; mailbox settings. Ingestion: Gmail only. |
| [Application and interview tracking](docs/tracking.md) | Track confirmations, replies, and events. | Selected Gmail, Calendar, or Messages tools. |
| [Apple Messages](docs/messages.md) | Read selected conversations; saved transcripts when exposed by the MCP. | **Mac + Messages MCP + database permission**. |
| [Reports](docs/report.md) | Summarize saves, updates, and gaps. | Chat; Gmail for opted-in self-email. |
| [Manual actions](docs/optional/manual-actions.md) | Prepare application pages or research recruiters. | Explicit request + signed-in computer use. |

**Computer use** means operating a browser through Codex. Google connectors and local Excel writes need no computer control. Runbooks start with requirements; [tool setup](docs/tools.md) links to connections.

## Where things live

| Folder | Purpose |
| --- | --- |
| [helpers/](helpers/) | The two discovery chats’ instructions. Separate research; one central writer. |
| [docs/](docs/source-map.md) | Feature guides, setup checks, and recovery. Read what you need. |
| [sheets/](sheets/) | Blank tracker and schema. Shared Jobs tab, plus tracking and provenance tabs. |
| [support/](support/README.md) | Setup, queue, save, and verification code. [Toolkit](support/toolkit/README.md) parses/checks evidence; no account connections. |

**Rated target companies starter (historical Blind 3.5+):** [103 companies](blind-companies.json), with personal notes removed. **Ratings are historical, user-supplied, and not freshly verified; their original dates are unknown.** [Onboarding](ONBOARDING.md) copies your chosen targets privately before use. See [rated target company setup](blind.md#setup).

**Required host:** Codex on macOS + Python 3.10+. Improve your materials separately in [Resume](../Resume/resume-content-optimization.md) and [LinkedIn](../LinkedIn/linkedin-profile-optimization.md).
