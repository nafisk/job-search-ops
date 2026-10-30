# Job Search Ops agent guidance

Read [README.md](README.md) and route to the user's goal. Basic discovery, fit review, and preparation run in the current session; do not route a small search through advanced onboarding.

| Request | Instructions |
| --- | --- |
| Find postings | [job-search](.agents/skills/job-search/SKILL.md) |
| Review supplied jobs | [job-fit-review](.agents/skills/job-fit-review/SKILL.md) |
| Prepare selected applications/open routes | [application-prep](.agents/skills/application-prep/SKILL.md) |
| Resume editing | Read the complete [resume runbook](Resume/resume-content-optimization.md), preserving factual review/approval rules. |
| LinkedIn profile work | Read the complete [LinkedIn runbook](LinkedIn/linkedin-profile-optimization.md); supplied-content review needs no account. |

## Basic skill boundaries

- No mandatory tracker, Python, multi-chat setup, schedule, ledger, or pilot. Each skill is independently usable. Missing capabilities degrade to useful supplied-text/chat output with verification gaps disclosed.
- Apply explicit user instructions > user-selected saved preferences > defaults. Examples are fictional, not active settings. Keep applicant facts separate from wishes; unknown evidence stays unknown.
- During development/testing, use fictional local cases. Do not research real jobs or connect accounts to validate instructions.
- Keep personal data outside installed skills and public exports. Preserve private files, saved choices, resources, user edits, and existing installations. Do not scan unrelated private records or silently adopt a deployment.
- Prep is draft/open-only: no autofill, upload, profile sync, agreements, or submission. Opening/preparing/closing never establishes Applied. Simplify is a user handoff, not a tested adapter.

## Advanced workflows: explicit opt-in

Only when the user chooses an advanced workflow or asks to operate an existing installation, follow its owning guides and scoped AGENTS.md. Do not remove safeguards or migrate state to make it behave like a basic skill.

| Advanced request | Guides |
| --- | --- |
| Alerts, shared tracking, installed job workflow | [Onboarding](<Application Workflow/ONBOARDING.md>), [run](<Application Workflow/run.md>), [guidance](<Application Workflow/AGENTS.md>), [operations](<Application Workflow/docs/operations.md>) |
| Installed rated-company research | [Blind onboarding](<Blind Company Research/ONBOARDING.md>) or [run](<Blind Company Research/run.md>); same central writer/tracker |
| Persistent application batches | [Batch onboarding](<Application Batches/ONBOARDING.md>) or [run](<Application Batches/run.md>); shared setup/pilot remain required for this advanced path |
| Recruiter research/drafts | [Outreach onboarding](<Recruiter Outreach/ONBOARDING.md>), [research](<Recruiter Outreach/research.md>), [drafting](<Recruiter Outreach/run.md>), [tracker](<Recruiter Outreach/tracker.md>) |

Connect only selected tools. Preserve IDs, private paths, one-writer ownership, uncertain effects, queues, history, referral holds, and unrelated schedules. Use the selected advanced guide's private setup-summary rules only for its setup. Basic skills never create/reset advanced state.

## Repository maintenance

Inspect Git status; preserve unrelated work. Do not commit/push unless requested. Keep three self-contained packages in `.agents/skills`, with concise entrypoints and conditional references. No dependency on sibling skills or legacy code.

Run [skill validation](docs/skill-validation.md). Review intended additions to the [release inventory](<Application Workflow/support/RELEASE_FILES.txt>); never add private files to satisfy it or weaken export checks. For advanced code changes, follow [verification](<Application Workflow/docs/verification.md>). Package/docs checks cannot certify live integrations or model behavior.
