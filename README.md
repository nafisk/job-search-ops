# Job Search Ops

Three independent agent skills for finding engineering jobs, reviewing fit, and preparing applications. Supply your resume and preferences in your current session. Basic use needs no Google Sheets, Python runtime, installation ledger, extra chats, or schedules.

| Skill | Use it for | Minimum capability |
| --- | --- | --- |
| [job-search](.agents/skills/job-search/SKILL.md) | Discover official postings; calibrate on three samples before a larger shortlist | Readable applicant facts; public search/full-page reads for verified live matches |
| [job-fit-review](.agents/skills/job-fit-review/SKILL.md) | Compare descriptions or URLs with specific resume evidence | Resume/facts and description text; URL reading optional |
| [application-prep](.agents/skills/application-prep/SKILL.md) | Draft truthful answers and verify/open chosen routes | Supplied job details and approved facts; browser optional |

Each skill includes its own instructions, conditional reference, and fictional preferences example. Install one without the others.

## Try a skill

Keep your resume outside the repository and installed skill folders. Attach it, supply text, or identify an accessible private file. If your host cannot read its format, supply text instead.

```text
Use $job-search with my attached resume. Find 10 backend or full-stack
Software Engineer roles at my chosen companies, in Example City or remote
within Example Country. Exclude support and sales roles. Show three samples
for calibration before completing the search. Return a chat table.
```

```text
Use $job-fit-review with my resume and these two pasted descriptions.
Compare required and preferred qualifications with specific evidence.
Tell me what is supported, unknown, or a genuine mismatch.
```

```text
Use $application-prep for these chosen job URLs and approved resume facts.
Check my supplied prior applications and referral restrictions. Draft answers
for review. If browser access exists, verify and open the routes for my
Simplify handoff. Do not fill or submit anything.
```

Search returns fewer matches instead of padding. Fit uses **strong match**, **plausible match**, **needs clarification**, or **mismatch**, without invented percentages. Missing live tools yields supplied-text review or search guidance with availability unverified. Preparation never autofills, uploads, accepts agreements, or submits; you operate Simplify and review/submit yourself.

## Installation

**Development status:** this redesign is local and uncommitted on `codex/ray-updates`. GitHub installation and fresh clones will not contain it until publication. Try the local files in this checkout now. The following instructions describe use after publication; this repository runs no installer.

### Clone and open in Codex

```sh
git clone --branch codex/ray-updates git@github.com:RaymondRJones/job-search-ops.git
cd job-search-ops
```

Open the checkout as your project/current working directory. Codex discovers repository skills in `.agents/skills`; invoke them by name. It detects changes automatically; restart if absent. Instructions were checked against the [official Codex skill guide](https://learn.chatgpt.com/docs/build-skills) on October 30, 2026; a fresh installation has not been tested.

If discovery is unavailable, ask your agent to read the exact `SKILL.md` and follow its references. This manual-instructions fallback is not a claim of native support in every host.

### Install one GitHub skill in Codex

After publication, ask the built-in installer:

```text
Use $skill-installer to install only job-search from repository
RaymondRJones/job-search-ops, ref codex/ray-updates,
path .agents/skills/job-search. Preserve existing installed skills.
```

Replace `job-search` in both places with `job-fit-review` or `application-prep`. Supply repo/ref/path separately to avoid ambiguity with branch names containing slashes. Each directory includes its required references. See [installation and host support](docs/installation.md) for evidence and limitations.

## Customize without setup

Plain-language preferences are enough. Optionally select a private copy of a skill's `preferences.example.yaml` and identify it to your agent. Examples are fictional and inactive; they never automatically become your profile.

Precedence: **explicit user instructions > saved preferences > defaults**. Per-request overrides do not overwrite saved files. Omitted applicant facts stay unknown. No sponsorship needed does not establish citizenship; total tenure does not establish years in a specific technology.

Default output is chat. Request CSV or tracker integration optionally; neither is required. Personal resumes, preferences, answers, and history belong outside installed skills and public exports.

## Advanced workflows remain available

Existing installations, records, resource IDs, and schedules are unchanged. Basic skills neither migrate nor operate them. Explicitly select an advanced guide for its original setup and safeguards:

- [Application Workflow](<Application Workflow/README.md>): alerts, shared trackers, evidence receipts, ongoing tracking.
- [Blind Company Research](<Blind Company Research/README.md>): rated-company research through that shared runtime.
- [Application Batches](<Application Batches/README.md>): persistent tab reservations and handoffs.
- [Recruiter Outreach](<Recruiter Outreach/README.md>): screened contacts and unsent drafts.
- [Resume](Resume/README.md) and [LinkedIn](LinkedIn/README.md): material-improvement runbooks.

[Onboarding](ONBOARDING.md) distinguishes basic use from advanced setup. Advanced ownership, recovery, and pilot rules remain in force inside those workflows; they are not prerequisites for these skills.

## Development and validation

The skills are instruction-only. Python below is a maintainer check, not a user prerequisite.

```sh
python3 scripts/validate_skills.py
python3 -B -m unittest discover -s tests/skills -v
```

See [design assessment](docs/skills-redesign.md) and [validation/scenarios](docs/skill-validation.md). Local checks do not prove model behavior, fresh installation, live integrations, Simplify support, or cross-agent compatibility.
