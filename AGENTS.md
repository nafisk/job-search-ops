# Job Search Ops agent guidance

Start with [README.md](README.md) to identify the requested workflow. For setup, use [ONBOARDING.md](ONBOARDING.md) and follow only the selected feature's guide. If the user's goal is already clear, route directly; do not repeat answered questions.

| Requested work | Authoritative instructions |
| --- | --- |
| Resume review/editing | Read the complete [resume runbook](Resume/resume-content-optimization.md). Preserve its factual review and editing approval rules. |
| LinkedIn review/editing | Read the complete [LinkedIn runbook](LinkedIn/linkedin-profile-optimization.md). Supplied-content review needs no live account access. |
| Job discovery and shared tracking | Read [Application Discovery guidance](<Application Discovery/AGENTS.md>) and follow its [onboarding](<Application Discovery/ONBOARDING.md>) or [central runbook](<Application Discovery/run.md>). For Blind, use the nested [setup](<Application Discovery/Blind Company Research/ONBOARDING.md>) or [research runbook](<Application Discovery/Blind Company Research/run.md>). |

## Setup and execution

- Reuse the selected user's confirmed facts and canonical private settings. Examples are shapes, not real choices, facts, accounts or authorization. Never substitute another person's deployment.
- LinkedIn alerts and Blind research are separate entry points into one jobs tracker. Keep the existing `email`, `portal` and `blind` source keys and source-specific policies. Blind research queues evidence; only central accepts and saves it. Do not initialize a second tracker or require email/referrals for a Blind-only setup.
- Connect only selected tools and respect the requested operation. Application Discovery's initialization, `doctor`, writer and scheduling rules do not apply to standalone Resume or LinkedIn work.
- Keep operational private data outside the repository and exports. Preserve existing locations, IDs, history, user edits and unrelated live workflows. Read only private material relevant to the selected scope.
- Follow each guide's setup, pilot and run boundaries. The user fills and submits applications. LinkedIn profile edits follow that runbook's reviewed approval process.
- Finish operational setup with the [private setup summary](ONBOARDING.md#your-setup-summary). Link authoritative records and report actual verification/gaps; the summary grants no permissions and overrides no execution holds.

## Repository maintenance

Inspect current changes before editing and preserve unrelated work. Keep procedures in the workflow that owns them. Use root files to route readers.

Check additions and moves against [RELEASE_FILES.txt](<Application Discovery/support/RELEASE_FILES.txt>). Follow the [verification guide](<Application Discovery/docs/verification.md>). Validate documentation and navigation offline.

After verifying a major change, make a local commit scoped to that work so it can be reverted independently. Include the commit hash in the handoff.
