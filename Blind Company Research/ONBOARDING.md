# Set up Blind company research

> **Required:** Codex desktop on macOS, Python 3.10+, the complete repository, a private writable folder outside it, public search/page reads and a supported browser. A shared Application Workflow installation supplies the queue and central tracker writer.
> **Runs in:** Codex app. Choose local Excel or Google Sheets for the shared jobs tracker.
> **Computer use:** Career pages that need interaction; you handle sign-in or permission prompts. Supplied starter ratings need no Blind account.

Use this guide to choose Blind research independently of LinkedIn alerts. The [shared operating rules](<../Application Workflow/docs/operations.md>) govern private storage, permissions, source evidence and the single writer. The [shared tool guide](../ONBOARDING.md#tools-for-your-choices) has installation links.

```text
Set up Blind company research with me using this guide. Ask one choice at a time.
Reuse my existing private Application Workflow installation if I have one.
I authorize the selected tracker/chats, their documented delegation and the scoped
setup pilot. Create only schedules I choose after successful checks and a pilot.
Do not enable email alerts, referrals or tracking sources unless I choose them.
Do not install tools, broaden permissions or change existing live workflows
without the required selected authorization. Return and save my setup summary.
```

## 1. Choose or reuse the shared installation

- **Starting fresh:** choose a permanent private folder and either local Excel or Google Sheets. The agent follows the [shared agent setup procedure](<../Application Workflow/docs/agent-setup.md>) directly, using your choices here. Blind alone is a valid discovery selection: enable `modules.blind`, keep central enabled, and leave unselected discovery/tracking sources disabled. Manual runs and chat reports are the defaults.
- **Already using Application Workflow:** supply the canonical private configuration path. Preserve your tracker, company copy, history, account bindings, chats and schedules. Use [preference updates](<../Application Workflow/docs/preferences.md>) for supported changes and their required replacement pilot. A new unbound research chat or changed storage/account needs the separately reviewed migration described there; do not edit initialized configuration or create a second installation to bypass it.

This is a separate research workflow using the existing shared runtime. It does not create a second jobs tracker or give the Blind chat tracker-write access. No LinkedIn alert setup, Gmail, referral list, Calendar or Messages connection is required unless you separately select those features.

## 2. Choose companies and job criteria

Choose the [103-company starter](blind-companies.json) or your own list. **Its ratings are historical, user-supplied and not freshly verified; original dates are unknown.** The agent copies your chosen list outside the repository, reviews enabled companies and binds the private copy. Never replace an existing personal list automatically or add private notes to the repo.

Confirm rating threshold, role families, excluded titles, locations and eligibility constraints, plus base/stretch experience policy. Search preferences do not change your actual qualifications. The [runbook's setup section](run.md#setup) owns the exact list format, provenance and policy rules; unknown dates stay unknown.

## 3. Verify the selected tools and handoff

The agent completes the existing [setup sequence](<../Application Workflow/docs/agent-setup.md>) and [tool checks](<../Application Workflow/docs/tools.md>) for these selections:

| Required for this choice | What is checked |
| --- | --- |
| All Blind research | Public search/page access, supported browser, Python and private working files |
| Local Excel tracker | The central chat's app-provided spreadsheet runtime and actual file save/readback; no Google account |
| Google Sheets tracker | The central chat's selected Drive/Sheets connection, workbook identity and actual save/readback |
| Separate research chat | Its private workspace and verified [producer handoff](<../Application Workflow/docs/handoffs.md#producer-handoff>) to central |
| Scheduling, if chosen | Only the requested workflow's schedule, after its tool checks and pilot |

Use the shared source key `blind`; runtime helpers stay in `Application Workflow/support/`. Check Blind readiness independently with `doctor --workflow blind` and the required configuration/evidence arguments. Its research does not require central's unrelated email access. Central must still pass its own relevant checks before saving results.

Before any source access, follow the [runbook's mandatory start check](run.md). Tool readiness never overrides a pending pilot gate. New software, connections and expanded permissions need their own selected authorization.

## 4. Pilot research, then save through central

1. Research a declared small scope with actual sources. Preserve gaps and do not insert fixture jobs when none qualify.
2. Verify the packet is durably handed off or queued, then have central save/read back accepted results and report them. Record the existing setup acceptance evidence; a queued packet alone does not prove the tracker works.
3. Complete the required scoped pilot checks for the selected installation. For an existing preference update, follow its exact replacement-pilot process; never put the pilot override in a schedule.
4. Choose manual mode or requested schedules. The research chat and central writer may have separate times. **A Blind-only schedule leaves packets waiting until the next central run; it does not schedule central for you.**

Save and return your [private setup summary](../ONBOARDING.md#your-setup-summary): canonical configuration/list paths, tracker, research and central chats, verified or pending checks, selected timing and exact next run requests using actual permanent paths. Keep pending checks visible; do not call the path ready until required evidence is accepted.

## 5. Use the results

Ask the configured research chat to read this folder's [runbook](run.md) and use your saved installation. Then ask central to read [Application Workflow/run.md](<../Application Workflow/run.md>) and import ready packets into your shared tracker. Both messages use the actual paths from your setup summary.

After the shared installation and initial pilot are complete, follow [Application Batches onboarding](<../Application Batches/ONBOARDING.md>) to open eligible applications from that tracker. Batches remains a separately requested manual workflow; you fill and submit.

## Change preferences

Use the shared [preference-update procedure](<../Application Workflow/docs/preferences.md>) for supported company-policy, source and timing changes, including required policy versions and replacement pilots. Preserve private target/history locations and existing bindings. A new folder in this repository does not authorize moving private data, regenerating saved prompts or changing live schedules. Refresh your setup summary only after the requested change is verified.
