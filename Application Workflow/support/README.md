# Local workflow support

**Required:** Python 3.10+ on the supported macOS host. Local Excel also needs Codex's bundled spreadsheet runtime.  
**Runs in:** Codex's local terminal; connected effects use only the selected tools in the runbooks.

Start with [onboarding](../ONBOARDING.md). These files support the agent; users do not install or run every helper.

## What each directory does

| Directory | Purpose |
| --- | --- |
| [job_search_ops/](job_search_ops/) | One command interface for setup, source handoffs, the shared queue, safe tracker saves and report receipts. |
| [toolkit/](toolkit/README.md) | Agent-invoked parsing, screening, portal and tracking checks. Pure local functions, not connected adapters. |
| [config/](config/README.md) | Fictional examples, settings schema and capability inventory. Real choices live privately. |
| [tests/](tests/) | Regression checks using fictional data and disposable workbooks. Not a daily task. |
| [scripts/](scripts/) | The local Excel editing bridge, optional template builder and distribution checker. |

## What the runtime code does

- **config, setup, doctor, preferences:** validate choices, plan only selected resources, bind verified results and prepare prompts/schedules and safely update existing choices.
- **queue:** preserve source handoffs, deduplicate jobs and keep one writer with recoverable journals.
- **sheets, google_tracking, local_excel:** apply the same tracker rules to the chosen backend and verify saved results.
- **referrals:** project one private company list into the watchlist and an accepted portal registry.
- **host_evidence, snapshots, bootstrap:** validate actual tool/file results, freeze reports and prepare/check the blank tracker.

The toolkit is used only for selected source work. Its profile validator is also imported directly by setup. Other helpers are called by the agent following their linked guides; they do not automatically run merely because they are present.

## Commands for agents and maintainers

Run from `Application Workflow/support/` (quote paths containing spaces):

```sh
python3 -m job_search_ops --help
python3 -B -m unittest discover -s tests -v
python3 -B toolkit/verify_offline.py
python3 -B scripts/verify_release.py
```

Python uses the standard library. Local Excel needs app-provided Node and spreadsheet tooling; Google Sheets uses connected tools. No extra Python packages or bundled MCP server are required. [Tool setup](../docs/tools.md) explains conditional dependencies.

The existing workbook is ready for setup. `build_template.mjs` is only for maintainers rebuilding it; `local_artifact.mjs` performs selected local Excel edits. `verify_release.py` checks the exact reviewed inventory, local links and the blank workbook. `export_release.py` packages only that inventory and checks its extracted output. Maintainers update [RELEASE_FILES.txt](RELEASE_FILES.txt) only after reviewing each intended addition; never regenerate it from an unreviewed private working directory. See [verification](../docs/verification.md) for coverage and live-check limits.
